from accounts.models import Profile


def is_administrator(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    try:
        return (
            user.is_staff
            and user.profile.role == "ADMIN"
            and user.has_perm("complaints.view_complaint")
        )
    except (AttributeError, Profile.DoesNotExist):
        return False


def is_student(user):
    if not user.is_authenticated or is_administrator(user):
        return False
    try:
        return user.profile.role == "STUDENT"
    except (AttributeError, Profile.DoesNotExist):
        return False
