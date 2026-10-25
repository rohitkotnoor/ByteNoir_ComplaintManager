from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from accounts.forms import (
    AdministratorAuthenticationForm,
    AdministratorRegistrationForm,
    RegistrationForm,
    StyledAuthenticationForm,
)
from accounts.permissions import is_administrator, is_student
from accounts.throttling import LoginThrottleMixin


class SignInView(LoginThrottleMixin, LoginView):
    template_name = "accounts/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


class AdministratorSignInView(LoginThrottleMixin, LoginView):
    template_name = "accounts/admin_login.html"
    authentication_form = AdministratorAuthenticationForm
    redirect_authenticated_user = False

    def form_valid(self, form):
        if not is_administrator(form.get_user()):
            form.add_error(
                None,
                "Your account is active, but administrator access is not enabled. Ask the system administrator to set your role, enable Staff status, and grant complaint viewing permission.",
            )
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("complaints:admin_dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["first_admin_setup_required"] = not get_user_model().objects.filter(is_superuser=True, is_active=True).exists()
        return context


class AdministratorRegisterView(FormView):
    template_name = "accounts/admin_register.html"
    form_class = AdministratorRegistrationForm
    success_url = reverse_lazy("accounts:admin_registration_submitted")

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            "Your administrator registration request was received. An existing administrator must approve it before you can sign in.",
        )
        return super().form_valid(form)


class AdministratorRegistrationSubmittedView(TemplateView):
    template_name = "accounts/admin_registration_submitted.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["first_admin_setup_required"] = not get_user_model().objects.filter(is_superuser=True, is_active=True).exists()
        return context


class RegisterView(FormView):
    template_name = "accounts/student_register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("accounts:dashboard")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(
            self.request,
            f"Your student account is ready. College Register Number: {user.profile.student_id}.",
        )
        return super().form_valid(form)


@login_required
def dashboard(request):
    if is_administrator(request.user):
        return redirect("complaints:admin_dashboard")
    if is_student(request.user):
        return redirect("complaints:student_dashboard")
    return render(request, "errors/access_denied.html", status=403)
