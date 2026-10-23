from pathlib import PurePosixPath

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.permissions import is_administrator
from complaints.escalations import escalate_overdue_complaints
from complaints.forms import AdminComplaintUpdateForm, ComplaintFilterForm, ComplaintForm
from complaints.models import (
    Complaint,
    ComplaintAssignmentHistory,
    ComplaintAttachment,
    ComplaintStatusHistory,
    Notification,
)
from complaints.notifications import notify_administrators, notify_user
from complaints.permissions import role_required


def filtered_complaints(request):
    form = ComplaintFilterForm(request.GET or None)
    queryset = Complaint.objects.select_related("student", "student__profile", "assigned_to").prefetch_related("attachments")
    if form.is_valid():
        data = form.cleaned_data
        if data.get("q"):
            term = data["q"].strip()
            visible_reporter_match = (
                Q(is_anonymous=False)
                & (
                    Q(student__username__icontains=term)
                    | Q(student__first_name__icontains=term)
                    | Q(student__last_name__icontains=term)
                )
            )
            queryset = queryset.filter(
                Q(reference__icontains=term)
                | Q(title__icontains=term)
                | Q(description__icontains=term)
                | visible_reporter_match
            )
        for field in ("status", "category", "priority", "assigned_department"):
            if data.get(field):
                queryset = queryset.filter(**{field: data[field]})
        if data.get("escalated") == "yes":
            queryset = queryset.filter(escalated_at__isnull=False)
        elif data.get("escalated") == "no":
            queryset = queryset.filter(escalated_at__isnull=True)
        if data.get("date_from"):
            queryset = queryset.filter(created_at__date__gte=data["date_from"])
        if data.get("date_to"):
            queryset = queryset.filter(created_at__date__lte=data["date_to"])
    return form, queryset


def paginated(request, queryset):
    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)
    return page_obj, query_params.urlencode()


@role_required("student")
def student_dashboard(request):
    complaints = Complaint.objects.filter(student=request.user)
    counts = {
        "total": complaints.count(),
        "pending": complaints.filter(status__in=[Complaint.Status.SUBMITTED, Complaint.Status.UNDER_REVIEW]).count(),
        "in_progress": complaints.filter(status=Complaint.Status.IN_PROGRESS).count(),
        "resolved": complaints.filter(status=Complaint.Status.RESOLVED).count(),
    }
    recent = complaints.select_related("assigned_to")[:5]
    return render(request, "complaints/student_dashboard.html", {"counts": counts, "recent": recent})


@role_required("student")
def complaint_create(request):
    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                complaint = form.save(commit=False)
                complaint.student = request.user
                complaint.status = Complaint.Status.SUBMITTED
                complaint.priority = form.cleaned_data["suggested_priority"]
                complaint.save()
                for uploaded_file in form.cleaned_data["attachments"]:
                    ComplaintAttachment.objects.create(
                        complaint=complaint,
                        original_name=uploaded_file.name[:255],
                        file=uploaded_file,
                    )
                ComplaintStatusHistory.objects.create(
                    complaint=complaint,
                    previous_status="",
                    new_status=complaint.status,
                    changed_by=request.user,
                    change_note="Complaint submitted.",
                )
                notify_administrators(
                    complaint,
                    f"New {complaint.get_category_display()} complaint {complaint.reference} submitted for {complaint.get_assigned_department_display()}.",
                )
            messages.success(request, f"Complaint {complaint.reference} was submitted.")
            return redirect("complaints:detail", reference=complaint.reference)
    else:
        form = ComplaintForm()
    return render(request, "complaints/complaint_form.html", {"form": form, "page_title": "Submit a complaint"})


@role_required("student")
def my_complaints(request):
    queryset = Complaint.objects.filter(student=request.user).select_related("assigned_to").prefetch_related("attachments")
    page_obj, query_string = paginated(request, queryset)
    return render(
        request,
        "complaints/complaint_list.html",
        {"page_obj": page_obj, "my_complaints": True, "admin_view": False, "query_string": query_string},
    )


def complaint_for_viewer(request, reference):
    queryset = Complaint.objects.select_related("student", "student__profile", "assigned_to").prefetch_related(
        "status_history__changed_by", "assignment_history__changed_by", "assignment_history__previous_assignee",
        "assignment_history__new_assignee", "attachments",
    )
    complaint = get_object_or_404(queryset, reference=reference)
    if not is_administrator(request.user) and complaint.student_id != request.user.pk:
        return None
    return complaint


@role_required("student")
def complaint_detail(request, reference):
    complaint = complaint_for_viewer(request, reference)
    if complaint is None:
        return render(request, "errors/access_denied.html", status=403)
    return render(request, "complaints/complaint_detail.html", {"complaint": complaint})


@role_required("student")
def complaint_edit(request, reference):
    complaint = get_object_or_404(Complaint, reference=reference, student=request.user)
    if complaint.status != Complaint.Status.SUBMITTED:
        messages.error(request, "This complaint can no longer be edited because it is under review.")
        return redirect("complaints:detail", reference=reference)
    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES, instance=complaint)
        if form.is_valid():
            original_category = complaint.category
            updated = form.save(commit=False)
            updated.priority = form.cleaned_data["suggested_priority"]
            if updated.category != original_category and not complaint.assigned_to_id:
                updated.assigned_department = Complaint.CATEGORY_DEPARTMENTS.get(
                    updated.category, Complaint.Department.GENERAL
                )
            updated.save()
            for uploaded_file in form.cleaned_data["attachments"]:
                ComplaintAttachment.objects.create(
                    complaint=complaint,
                    original_name=uploaded_file.name[:255],
                    file=uploaded_file,
                )
            messages.success(request, "Your complaint details were updated.")
            return redirect("complaints:detail", reference=reference)
    else:
        form = ComplaintForm(instance=complaint)
    return render(request, "complaints/complaint_form.html", {"form": form, "page_title": "Edit complaint", "complaint": complaint})


@role_required("admin")
def admin_dashboard(request):
    escalate_overdue_complaints()
    all_complaints = Complaint.objects.all()
    counts = {
        "total": all_complaints.count(),
        "pending": all_complaints.filter(status__in=[Complaint.Status.SUBMITTED, Complaint.Status.UNDER_REVIEW]).count(),
        "in_progress": all_complaints.filter(status=Complaint.Status.IN_PROGRESS).count(),
        "resolved": all_complaints.filter(status=Complaint.Status.RESOLVED).count(),
        "attention": all_complaints.filter(priority__in=[Complaint.Priority.HIGH, Complaint.Priority.URGENT]).exclude(
            status__in=[Complaint.Status.RESOLVED, Complaint.Status.REJECTED]
        ).count(),
        "escalated": all_complaints.filter(escalated_at__isnull=False).count(),
    }
    form, queryset = filtered_complaints(request)
    page_obj, query_string = paginated(request, queryset)
    return render(
        request,
        "complaints/admin_dashboard.html",
        {"counts": counts, "page_obj": page_obj, "filter_form": form, "query_string": query_string},
    )


@role_required("admin")
def admin_complaint_list(request):
    escalate_overdue_complaints()
    form, queryset = filtered_complaints(request)
    page_obj, query_string = paginated(request, queryset)
    return render(
        request,
        "complaints/complaint_list.html",
        {"page_obj": page_obj, "my_complaints": False, "admin_view": True, "filter_form": form, "query_string": query_string},
    )


@role_required("admin", permission="complaints.change_complaint")
def admin_complaint_detail(request, reference):
    escalate_overdue_complaints()
    complaint = get_object_or_404(
        Complaint.objects.select_related("student", "student__profile", "assigned_to").prefetch_related(
            "attachments", "status_history__changed_by", "assignment_history__changed_by",
            "assignment_history__previous_assignee", "assignment_history__new_assignee",
        ),
        reference=reference,
    )
    old_status = complaint.status
    old_priority = complaint.priority
    old_response = complaint.admin_response
    old_department = complaint.assigned_department
    old_assignee = complaint.assigned_to
    if request.method == "POST":
        form = AdminComplaintUpdateForm(request.POST, instance=complaint)
        if form.is_valid():
            with transaction.atomic():
                updated = form.save(commit=False)
                updated.save()
                status_changed = old_status != updated.status
                priority_changed = old_priority != updated.priority
                response_changed = old_response != updated.admin_response
                assignment_changed = (
                    old_department != updated.assigned_department or old_assignee != updated.assigned_to
                )
                if status_changed:
                    ComplaintStatusHistory.objects.create(
                        complaint=updated,
                        previous_status=old_status,
                        new_status=updated.status,
                        changed_by=request.user,
                        change_note=form.cleaned_data["change_note"],
                    )
                if assignment_changed:
                    ComplaintAssignmentHistory.objects.create(
                        complaint=updated,
                        previous_department=old_department,
                        new_department=updated.assigned_department,
                        previous_assignee=old_assignee,
                        new_assignee=updated.assigned_to,
                        changed_by=request.user,
                        change_note=form.cleaned_data["change_note"],
                    )
                    if updated.assigned_to_id:
                        notify_user(
                            updated.assigned_to,
                            updated,
                            f"Complaint {updated.reference} has been assigned to you in {updated.get_assigned_department_display()}.",
                        )

                student_updates = []
                if status_changed:
                    student_updates.append(f"status changed to {updated.get_status_display()}")
                if priority_changed:
                    student_updates.append(f"priority changed to {updated.get_priority_display()}")
                if response_changed:
                    student_updates.append("an administrator added a response")
                if assignment_changed:
                    student_updates.append(f"assigned to {updated.get_assigned_department_display()}")
                if student_updates:
                    notify_user(
                        updated.student,
                        updated,
                        f"Complaint {updated.reference}: " + "; ".join(student_updates) + ".",
                    )
                if (
                    updated.assigned_to_id
                    and updated.assigned_to_id != request.user.pk
                    and not assignment_changed
                    and (status_changed or priority_changed or response_changed)
                ):
                    notify_user(
                        updated.assigned_to,
                        updated,
                        f"Complaint {updated.reference} was updated: " + "; ".join(student_updates) + ".",
                    )
            messages.success(request, f"Complaint {complaint.reference} was updated.")
            return redirect("complaints:admin_detail", reference=reference)
    else:
        form = AdminComplaintUpdateForm(instance=complaint)
    return render(request, "complaints/admin_detail.html", {"complaint": complaint, "form": form})


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).select_related("complaint")
    return render(
        request,
        "complaints/notification_list.html",
        {"notifications": notifications, "admin_view": is_administrator(request.user)},
    )


@login_required
@require_POST
def notification_mark_read(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=("read_at",))
    return redirect("complaints:notifications")


@login_required
def attachment_download(request, attachment_id):
    attachment = get_object_or_404(
        ComplaintAttachment.objects.select_related("complaint", "complaint__student"), pk=attachment_id
    )
    if not is_administrator(request.user) and attachment.complaint.student_id != request.user.pk:
        return render(request, "errors/access_denied.html", status=403)
    try:
        attachment.file.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404("Attachment is unavailable.")
    if attachment.complaint.is_anonymous and is_administrator(request.user):
        extension = PurePosixPath(attachment.file.name).suffix
        filename = f"anonymous-attachment-{attachment.pk}{extension}"
    else:
        filename = PurePosixPath(attachment.original_name.replace("\\", "/")).name
    return FileResponse(attachment.file, as_attachment=True, filename=filename)
