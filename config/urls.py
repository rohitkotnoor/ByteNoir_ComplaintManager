from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from config.views import custom_403, custom_404

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("accounts/", include("accounts.urls")),
    path("complaints/", include("complaints.urls")),
]

handler403 = custom_403
handler404 = custom_404
