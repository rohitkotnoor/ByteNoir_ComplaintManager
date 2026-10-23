from pathlib import PurePath

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from complaints.models import Complaint
from complaints.notifications import administrators

User = get_user_model()


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(item, initial) for item in files]


class ComplaintForm(forms.ModelForm):
    suggested_priority = forms.ChoiceField(
        choices=(
            (Complaint.Priority.LOW, "Low"),
            (Complaint.Priority.MEDIUM, "Medium"),
            (Complaint.Priority.HIGH, "High"),
        ),
        label="Suggested priority",
        help_text="Administrators may adjust this after review.",
        required=False,
    )
    attachments = MultipleFileField(
        required=False,
        label="Attachments",
        help_text="Up to 5 files, 10 MB each. Accepted: JPG, PNG, WebP, and PDF.",
    )

    class Meta:
        model = Complaint
        fields = ("title", "description", "category", "is_anonymous")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 7}),
            "is_anonymous": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.priority in dict(self.fields["suggested_priority"].choices):
            self.initial["suggested_priority"] = self.instance.priority
        else:
            self.initial["suggested_priority"] = Complaint.Priority.MEDIUM
        self.fields["is_anonymous"].label = "Submit anonymously"
        self.fields["is_anonymous"].help_text = "Your account can still track this report. Administrators will not see your profile or original file names; leave identifying details out of the report and attachments."

    def clean_attachments(self):
        files = self.cleaned_data.get("attachments", [])
        existing_count = self.instance.attachments.count() if self.instance.pk else 0
        if existing_count + len(files) > 5:
            raise ValidationError("A complaint can have at most 5 attachments.")
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
        for uploaded_file in files:
            if PurePath(uploaded_file.name).suffix.lower() not in allowed_extensions:
                raise ValidationError("Use JPG, PNG, WebP, or PDF files only.")
            if uploaded_file.size > 10 * 1024 * 1024:
                raise ValidationError("Each attachment must be 10 MB or smaller.")
        return files

    def clean_suggested_priority(self):
        value = self.cleaned_data.get("suggested_priority")
        if value:
            return value
        if self.instance.pk and self.instance.priority in dict(self.fields["suggested_priority"].choices):
            return self.instance.priority
        return Complaint.Priority.MEDIUM


class AdminComplaintUpdateForm(forms.ModelForm):
    change_note = forms.CharField(
        required=False,
        max_length=500,
        label="Update note",
        help_text="Optional note recorded with status or assignment changes.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    class Meta:
        model = Complaint
        fields = ("status", "priority", "assigned_department", "assigned_to", "admin_response")
        widgets = {"admin_response": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_department"].label = "Assigned department"
        self.fields["assigned_to"].label = "Assigned administrator"
        self.fields["assigned_to"].required = False
        self.fields["assigned_to"].queryset = User.objects.filter(
            pk__in=[user.pk for user in administrators()]
        ).order_by("username")


class ComplaintFilterForm(forms.Form):
    status = forms.ChoiceField(required=False, choices=[("", "All statuses"), *Complaint.Status.choices])
    category = forms.ChoiceField(required=False, choices=[("", "All categories"), *Complaint.Category.choices])
    priority = forms.ChoiceField(required=False, choices=[("", "All priorities"), *Complaint.Priority.choices])
    assigned_department = forms.ChoiceField(
        required=False,
        choices=[("", "All departments"), *Complaint.Department.choices],
        label="Department",
    )
    escalated = forms.ChoiceField(
        required=False,
        choices=(("", "All cases"), ("yes", "Escalated"), ("no", "Not escalated")),
        label="Escalation",
    )
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="From")
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="To")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("date_from") and cleaned.get("date_to") and cleaned["date_from"] > cleaned["date_to"]:
            self.add_error("date_to", "The end date must be on or after the start date.")
        return cleaned
