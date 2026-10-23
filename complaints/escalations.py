from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from complaints.models import Complaint, Notification
from complaints.notifications import administrators, notify_user


def escalate_overdue_complaints(now=None):
    now = now or timezone.now()
    threshold = now - timedelta(hours=getattr(settings, "COMPLAINT_ESCALATION_HOURS", 48))
    candidates = Complaint.objects.filter(
        escalated_at__isnull=True,
        created_at__lte=threshold,
    ).exclude(status__in=(Complaint.Status.RESOLVED, Complaint.Status.REJECTED))
    escalated_count = 0

    for candidate in candidates.iterator():
        with transaction.atomic():
            complaint = Complaint.objects.select_for_update().select_related("student").get(pk=candidate.pk)
            if complaint.escalated_at or not complaint.is_open or complaint.created_at > threshold:
                continue
            complaint.escalated_at = now
            complaint.priority = Complaint.Priority.URGENT
            complaint.save(update_fields=("escalated_at", "priority", "updated_at"))
            message = f"{complaint.reference} has been escalated after exceeding the resolution window."
            Notification.objects.bulk_create(
                [Notification(user=user, complaint=complaint, message=message) for user in administrators()]
            )
            notify_user(
                complaint.student,
                complaint,
                f"Your complaint {complaint.reference} has been escalated for additional attention.",
            )
            escalated_count += 1
    return escalated_count
