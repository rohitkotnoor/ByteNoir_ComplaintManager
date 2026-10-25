import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from accounts.models import LoginAttempt


class LoginThrottleMixin:
    """Throttle repeated failed logins by account and account/source-IP pair."""

    login_attempt_window = timedelta(minutes=15)
    login_pair_limit = 5
    login_account_limit = 15

    def _login_throttle_keys(self, request):
        username = request.POST.get("username", "").strip().casefold()
        remote_ip = request.META.get("REMOTE_ADDR", "unknown").strip() or "unknown"
        secret = settings.SECRET_KEY.encode("utf-8")

        def digest(value):
            return hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()

        return digest(username), digest(remote_ip)

    def _is_login_throttled(self, username_hash, ip_hash):
        cutoff = timezone.now() - self.login_attempt_window
        recent = LoginAttempt.objects.filter(attempted_at__gte=cutoff)
        return (
            recent.filter(username_hash=username_hash, ip_hash=ip_hash).count() >= self.login_pair_limit
            or recent.filter(username_hash=username_hash).count() >= self.login_account_limit
        )

    def post(self, request, *args, **kwargs):
        self._throttle_username_hash, self._throttle_ip_hash = self._login_throttle_keys(request)
        self._throttle_blocked = self._is_login_throttled(
            self._throttle_username_hash,
            self._throttle_ip_hash,
        )
        if self._throttle_blocked:
            form = self.get_form_class()(request=request)
            form.add_error(None, "Too many failed sign-in attempts. Please wait 15 minutes and try again.")
            return self.form_invalid(form)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        if hasattr(self, "_throttle_username_hash") and not getattr(self, "_throttle_blocked", False):
            now = timezone.now()
            LoginAttempt.objects.filter(attempted_at__lt=now - timedelta(hours=1)).delete()
            LoginAttempt.objects.create(
                username_hash=self._throttle_username_hash,
                ip_hash=self._throttle_ip_hash,
                attempted_at=now,
            )
        return super().form_invalid(form)

    def form_valid(self, form):
        if hasattr(self, "_throttle_username_hash"):
            LoginAttempt.objects.filter(username_hash=self._throttle_username_hash).delete()
        return super().form_valid(form)
