import uuid
from pathlib import PurePath

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator


class Complaint(models.Model):
    class Category(models.TextChoices):
        HOSTEL = "HOSTEL", "Hostel"
        CLASSROOMS = "CLASSROOMS", "Classrooms"
        MESS = "MESS", "Mess / Food"
        ACADEMICS = "ACADEMICS", "Academics"
        INFRASTRUCTURE = "INFRASTRUCTURE", "Infrastructure"
        LIBRARY = "LIBRARY", "Library"
        INTERNET = "INTERNET", "Internet / Wi-Fi"
        CLEANLINESS = "CLEANLINESS", "Cleanliness"
        ADMINISTRATION = "ADMINISTRATION", "Administration"
        OTHER = "OTHER", "Other"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        REJECTED = "REJECTED", "Rejected"

    class Department(models.TextChoices):
        HOSTEL = "HOSTEL", "Hostel Office"
        DINING = "DINING", "Dining Services"
        ACADEMIC = "ACADEMIC", "Academic Affairs"
        FACILITIES = "FACILITIES", "Facilities & Maintenance"
        LIBRARY = "LIBRARY", "Library"
        IT = "IT", "IT Services"
        HOUSEKEEPING = "HOUSEKEEPING", "Housekeeping"
        ADMINISTRATION = "ADMINISTRATION", "Administration"
        GENERAL = "GENERAL", "General Services"

    CATEGORY_DEPARTMENTS = {
        Category.HOSTEL: Department.HOSTEL,
        Category.CLASSROOMS: Department.FACILITIES,
        Category.MESS: Department.DINING,
        Category.ACADEMICS: Department.ACADEMIC,
        Category.INFRASTRUCTURE: Department.FACILITIES,
        Category.LIBRARY: Department.LIBRARY,
        Category.INTERNET: Department.IT,
        Category.CLEANLINESS: Department.HOUSEKEEPING,
        Category.ADMINISTRATION: Department.ADMINISTRATION,
        Category.OTHER: Department.GENERAL,
    }

    reference = models.CharField(max_length=24, unique=True, editable=False, blank=True)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaints")
    title = models.CharField(max_length=160)
    description = models.TextField(max_length=5000)
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM, db_index=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    is_anonymous = models.BooleanField(default=False, help_text="Hide the reporter's identity from administrators.")
    assigned_department = models.CharField(max_length=20, choices=Department.choices, blank=True, db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
    )
    escalated_at = models.DateTimeField(null=True, blank=True, db_index=True)
    admin_response = models.TextField(blank=True, max_length=5000)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("status", "created_at")), models.Index(fields=("student", "created_at"))]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"CC-{timezone.localdate():%Y%m}-{uuid.uuid4().hex[:7].upper()}"
        if not self.assigned_department and self.category:
            self.assigned_department = self.CATEGORY_DEPARTMENTS.get(self.category, self.Department.GENERAL)
        super().save(*args, **kwargs)

    @property
    def escalation_deadline(self):
        from datetime import timedelta

        hours = getattr(settings, "COMPLAINT_ESCALATION_HOURS", 48)
        return self.created_at + timedelta(hours=hours)

    @property
    def is_open(self):
        return self.status not in (self.Status.RESOLVED, self.Status.REJECTED)

    def __str__(self):
        return f"{self.reference} — {self.title}"


class ComplaintStatusHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="status_history")
    previous_status = models.CharField(max_length=15, choices=Complaint.Status.choices, blank=True)
    new_status = models.CharField(max_length=15, choices=Complaint.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="complaint_status_changes")
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    change_note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ("timestamp", "pk")

    def __str__(self):
        old = self.get_previous_status_display() if self.previous_status else "Created"
        return f"{self.complaint.reference}: {old} → {self.get_new_status_display()}"


def attachment_upload_to(instance, filename):
    extension = PurePath(filename).suffix.lower()
    return f"complaint_attachments/{instance.complaint.reference}/{uuid.uuid4().hex}{extension}"


class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(
        upload_to=attachment_upload_to,
        validators=[FileExtensionValidator(allowed_extensions=("jpg", "jpeg", "png", "webp", "pdf"))],
    )
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("uploaded_at", "pk")

    def __str__(self):
        return self.original_name


class ComplaintAssignmentHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="assignment_history")
    previous_department = models.CharField(max_length=20, choices=Complaint.Department.choices, blank=True)
    new_department = models.CharField(max_length=20, choices=Complaint.Department.choices)
    previous_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="previous_complaint_assignments",
    )
    new_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_complaint_assignments",
    )
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="complaint_assignment_changes")
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    change_note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ("timestamp", "pk")


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="complaint_notifications")
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        indexes = [models.Index(fields=("user", "read_at", "created_at"))]

    def __str__(self):
        return f"{self.user}: {self.message}"
