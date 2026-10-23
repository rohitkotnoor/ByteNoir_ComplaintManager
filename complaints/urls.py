from django.urls import path

from complaints import views

app_name = "complaints"

urlpatterns = [
    path("notifications/", views.notification_list, name="notifications"),
    path("notifications/<int:notification_id>/read/", views.notification_mark_read, name="notification_read"),
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("new/", views.complaint_create, name="create"),
    path("mine/", views.my_complaints, name="mine"),
    path("<str:reference>/", views.complaint_detail, name="detail"),
    path("<str:reference>/edit/", views.complaint_edit, name="edit"),
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/all/", views.admin_complaint_list, name="admin_list"),
    path("admin/<str:reference>/", views.admin_complaint_detail, name="admin_detail"),
    path("attachments/<int:attachment_id>/", views.attachment_download, name="attachment_download"),
]
