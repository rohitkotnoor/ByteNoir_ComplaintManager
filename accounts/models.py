from django.conf import settings
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        ADMIN = "ADMIN", "Administrator"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    student_id = models.CharField("College Register Number", max_length=30, blank=True, unique=True, null=True)
    department = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class LoginAttempt(models.Model):
    username_hash = models.CharField(max_length=64)
    ip_hash = models.CharField(max_length=64)
    attempted_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=("username_hash", "ip_hash", "attempted_at"), name="acct_login_pair_idx"),
            models.Index(fields=("username_hash", "attempted_at"), name="acct_login_user_idx"),
            models.Index(fields=("ip_hash", "attempted_at"), name="acct_login_ip_idx"),
        ]
