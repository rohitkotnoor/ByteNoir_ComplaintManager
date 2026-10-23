from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Profile

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(
            user=instance,
            role=Profile.Role.ADMIN if instance.is_superuser else Profile.Role.STUDENT,
        )
    else:
        Profile.objects.get_or_create(
            user=instance,
            defaults={"role": Profile.Role.ADMIN if instance.is_superuser else Profile.Role.STUDENT},
        )
