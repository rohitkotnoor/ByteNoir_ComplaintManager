from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile

User = get_user_model()


class RegistrationAndLoginTests(TestCase):
    def test_student_registration_creates_student_profile_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "mira",
                "first_name": "Mira",
                "last_name": "Rao",
                "email": "mira@example.edu",
                "student_id": "STU-410",
                "department": "Physics",
                "password1": "SafePass_410!Stone",
                "password2": "SafePass_410!Stone",
                "role": "ADMIN",
                "is_staff": "true",
            },
        )
        self.assertRedirects(response, reverse("accounts:dashboard"), fetch_redirect_response=False)
        user = User.objects.get(username="mira")
        self.assertTrue(user.check_password("SafePass_410!Stone"))
        self.assertFalse(user.is_staff)
        self.assertEqual(user.profile.role, Profile.Role.STUDENT)
        self.assertEqual(user.profile.student_id, "STU-410")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_invalid_registration_does_not_create_a_user(self):
        response = self.client.post(
            reverse("accounts:register"),
            {"username": "mira", "first_name": "Mira", "last_name": "Rao", "email": "bad", "password1": "one", "password2": "two"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="mira").exists())

    def test_existing_user_can_log_in(self):
        user = User.objects.create_user(username="loginstudent", password="SafePass_410!Stone")
        response = self.client.post(reverse("accounts:login"), {"username": user.username, "password": "SafePass_410!Stone"})
        self.assertRedirects(response, reverse("accounts:dashboard"), fetch_redirect_response=False)
        dashboard_response = self.client.get(reverse("accounts:dashboard"), follow=True)
        self.assertEqual(dashboard_response.status_code, 200)


class ProfileSignalTests(TestCase):
    def test_superuser_receives_administrator_profile(self):
        admin = User.objects.create_superuser(username="root", email="root@example.edu", password="SafePass_410!Stone")
        self.assertEqual(admin.profile.role, Profile.Role.ADMIN)
