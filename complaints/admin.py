from django.contrib import admin

from complaints.models import Complaint, ComplaintStatusHistory


class ComplaintStatusHistoryInline(admin.TabularInline):
    model = ComplaintStatusHistory
    extra = 0
    can_delete = False
    show_change_link = False
    fields = ("previous_status", "new_status", "actor", "timestamp", "change_note")
    readonly_fields = fields

    @admin.display(description="Changed by")
    def actor(self, obj):
        if obj.complaint.is_anonymous and obj.changed_by_id == obj.complaint.student_id:
            return "Anonymous reporter"
        return obj.changed_by.get_full_name() or obj.changed_by.username


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("reference", "title", "reporter", "category", "assigned_department", "priority", "status", "escalated", "created_at")
    list_filter = ("status", "category", "priority", "assigned_department", "escalated_at", "created_at")
    search_fields = ("reference", "title", "description")
    readonly_fields = tuple(field.name for field in Complaint._meta.fields) + ("reporter",)
    inlines = (ComplaintStatusHistoryInline,)

    def get_fields(self, request, obj=None):
        return (
            "reference", "title", "reporter", "is_anonymous", "description", "category", "priority", "status",
            "assigned_department", "assigned_to", "escalated_at", "admin_response", "created_at", "updated_at",
        )

    @admin.display(description="Student", ordering="student__username")
    def reporter(self, obj):
        if obj.is_anonymous:
            return "Anonymous reporter"
        return obj.student.get_full_name() or obj.student.username

    @admin.display(boolean=True, description="Escalated", ordering="escalated_at")
    def escalated(self, obj):
        return bool(obj.escalated_at)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
