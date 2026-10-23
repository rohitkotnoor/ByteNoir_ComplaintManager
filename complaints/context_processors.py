from django.conf import settings

from complaints.models import Notification


def unread_complaint_notifications(request):
    if not request.user.is_authenticated:
        return {
            "unread_notification_count": 0,
            "complaint_escalation_hours": getattr(settings, "COMPLAINT_ESCALATION_HOURS", 48),
        }
    return {
        "unread_notification_count": Notification.objects.filter(user=request.user, read_at__isnull=True).count(),
        "complaint_escalation_hours": getattr(settings, "COMPLAINT_ESCALATION_HOURS", 48),
    }
