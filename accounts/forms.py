from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction

from accounts.models import Profile

User = get_user_model()


class RegistrationForm(UserCreationForm):
    student_id = forms.CharField(
        max_length=30,
        label="College Register Number",
        help_text="Enter the register number issued by your college.",
    )
    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, label="Last name")
    email = forms.EmailField()
    department = forms.CharField(max_length=100, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("student_id", "username", "first_name", "last_name", "email", "department")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(("student_id", "first_name", "last_name", "username", "email", "department", "password1", "password2"))

    def clean_student_id(self):
        value = self.cleaned_data["student_id"].strip()
        if Profile.objects.filter(student_id__iexact=value).exists():
            raise forms.ValidationError("This college register number is already registered.")
        return value

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.first_name = self.cleaned_data["first_name"].strip()
            user.last_name = self.cleaned_data["last_name"].strip()
            user.email = self.cleaned_data["email"].strip()
            user.save(update_fields=["first_name", "last_name", "email"])
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = Profile.Role.STUDENT
            profile.student_id = self.cleaned_data["student_id"] or None
            profile.department = self.cleaned_data["department"].strip()
            profile.save()
        return user


class AdministratorRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, label="Last name")
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.email = self.cleaned_data["email"].strip()
        user.is_active = False
        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = Profile.Role.ADMIN
            profile.save(update_fields=["role"])
        return user


class StyledAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}))

    class Meta:
        fields = ("username", "password")


class AdministratorAuthenticationForm(StyledAuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        try:
            return super().clean()
        except forms.ValidationError:
            if username and password:
                user = User._default_manager.filter(username__iexact=username).first()
                if user and not user.is_active and user.check_password(password):
                    try:
                        is_admin_request = user.profile.role == Profile.Role.ADMIN
                    except Profile.DoesNotExist:
                        is_admin_request = False
                    if is_admin_request:
                        raise forms.ValidationError(
                            "Your administrator request is awaiting approval. An existing administrator must activate your account before you can sign in."
                        )
            raise
