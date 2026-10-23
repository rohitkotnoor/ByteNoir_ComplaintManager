from django.contrib.auth.views import LogoutView
from django.urls import path

from accounts.views import (
    AdministratorRegisterView,
    AdministratorRegistrationSubmittedView,
    AdministratorSignInView,
    RegisterView,
    SignInView,
    dashboard,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("register/administrator/", AdministratorRegisterView.as_view(), name="admin_register"),
    path("register/administrator/submitted/", AdministratorRegistrationSubmittedView.as_view(), name="admin_registration_submitted"),
    path("login/", SignInView.as_view(), name="login"),
    path("login/administrator/", AdministratorSignInView.as_view(), name="admin_login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard/", dashboard, name="dashboard"),
]
