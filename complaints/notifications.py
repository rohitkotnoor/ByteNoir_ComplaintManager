from django.contrib.auth import get_user_model
from django.db.models import Q

from complaints.models import Notification

User = get_user_model()


def administrators():
    candidates = User.objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(is_staff=True, profile__role="ADMIN")
    ).distinct()
    return [
        user
        for user in candidates
        if user.has_perm("complaints.view_complaint") and user.has_perm("complaints.change_complaint")
    ]


def notify_user(user, complaint, message):
    if user and user.is_active:
        Notification.objects.create(user=user, complaint=complaint, message=message[:255])


def notify_administrators(complaint, message):
    Notification.objects.bulk_create(
        [Notification(user=user, complaint=complaint, message=message[:255]) for user in administrators()]
    )
