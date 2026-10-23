from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.permissions import is_administrator, is_student


def role_required(role, permission=None):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            allowed = is_administrator(request.user) if role == "admin" else is_student(request.user)
            if allowed and permission:
                allowed = request.user.has_perm(permission)
            if not allowed:
                return render(request, "errors/access_denied.html", status=403)
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
