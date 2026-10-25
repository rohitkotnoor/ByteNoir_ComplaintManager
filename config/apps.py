from django.contrib.admin.apps import AdminConfig


class ComplaintAdminConfig(AdminConfig):
    default_site = "config.admin_site.ThrottledAdminSite"
