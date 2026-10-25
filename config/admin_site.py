from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache

from accounts.throttling import LoginThrottleMixin


class ThrottledAdminLoginView(LoginThrottleMixin, LoginView):
    pass


class ThrottledAdminSite(AdminSite):
    @method_decorator(never_cache)
    @login_not_required
    def login(self, request, extra_context=None):
        if request.method == "GET" and self.has_permission(request):
            index_path = reverse("admin:index", current_app=self.name)
            return HttpResponseRedirect(index_path)

        context = {
            **self.each_context(request),
            "title": _("Log in"),
            "subtitle": None,
            "app_path": request.get_full_path(),
            "username": request.user.get_username(),
        }
        if "next" not in request.GET and "next" not in request.POST:
            context["next"] = reverse("admin:index", current_app=self.name)
        context.update(extra_context or {})

        defaults = {
            "extra_context": context,
            "authentication_form": self.login_form or AdminAuthenticationForm,
            "template_name": self.login_template or "admin/login.html",
        }
        request.current_app = self.name
        return ThrottledAdminLoginView.as_view(**defaults)(request)
