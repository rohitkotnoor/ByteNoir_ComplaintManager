from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from complaints.models import Complaint, ComplaintStatusHistory

User = get_user_model()
PASSWORD = "SafePass_410!Stone"


def make_student(username):
    return User.objects.create_user(username=username, password=PASSWORD)


def make_admin(username="admin"):
    user = User.objects.create_superuser(username=username, email=f"{username}@example.edu", password=PASSWORD)
    return user


def make_complaint(student, **overrides):
    defaults = {
        "title": "Library door is broken",
        "description": "The north entrance door does not close securely after 18:00.",
        "category": Complaint.Category.INFRASTRUCTURE,
    }
    defaults.update(overrides)
    return Complaint.objects.create(student=student, **defaults)


class ComplaintWorkflowTests(TestCase):
    def setUp(self):
        self.student = make_student("student-one")
        self.other_student = make_student("student-two")
        self.admin = make_admin()

    def test_student_can_submit_complaint_and_history_is_created(self):
        self.client.login(username="student-one", password=PASSWORD)
        response = self.client.post(
            reverse("complaints:create"),
            {
                "title": "Wi-Fi disconnects",
                "description": "The network in the east wing disconnects repeatedly during lectures.",
                "category": Complaint.Category.INTERNET,
                "status": Complaint.Status.RESOLVED,
                "priority": Complaint.Priority.URGENT,
            },
        )
        complaint = Complaint.objects.get(title="Wi-Fi disconnects")
        self.assertRedirects(response, reverse("complaints:detail", args=[complaint.reference]))
        self.assertTrue(complaint.reference.startswith("CC-"))
        self.assertEqual(complaint.student, self.student)
        self.assertEqual(complaint.status, Complaint.Status.SUBMITTED)
        self.assertEqual(complaint.priority, Complaint.Priority.MEDIUM)
        self.assertEqual(complaint.status_history.count(), 1)
        self.assertEqual(complaint.status_history.first().changed_by, self.student)

    def test_invalid_complaint_form_is_rejected(self):
        self.client.login(username="student-one", password=PASSWORD)
        response = self.client.post(reverse("complaints:create"), {"title": "", "description": "short", "category": "NOT_A_CATEGORY"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Complaint.objects.count(), 0)

    def test_student_can_access_own_complaint(self):
        complaint = make_complaint(self.student)
        self.client.login(username="student-one", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("complaints:detail", args=[complaint.reference])).status_code, 200)

    def test_student_complaint_list_contains_only_their_records(self):
        own = make_complaint(self.student)
        other = make_complaint(self.other_student, title="Private concern from another student")
        self.client.login(username="student-one", password=PASSWORD)
        response = self.client.get(reverse("complaints:mine"))
        self.assertContains(response, own.reference)
        self.assertNotContains(response, other.reference)

    def test_student_is_denied_another_students_complaint(self):
        complaint = make_complaint(self.other_student)
        self.client.login(username="student-one", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("complaints:detail", args=[complaint.reference])).status_code, 403)
        self.assertEqual(self.client.get(reverse("complaints:edit", args=[complaint.reference])).status_code, 404)

    def test_student_cannot_open_administrator_pages(self):
        self.client.login(username="student-one", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("complaints:admin_dashboard")).status_code, 403)
        self.assertEqual(self.client.get(reverse("complaints:admin_list")).status_code, 403)

    def test_administrator_updates_status_priority_and_history(self):
        complaint = make_complaint(self.student)
        self.client.login(username="admin", password=PASSWORD)
        response = self.client.post(
            reverse("complaints:admin_detail", args=[complaint.reference]),
            {
                "status": Complaint.Status.IN_PROGRESS,
                "priority": Complaint.Priority.URGENT,
                "admin_response": "Facilities has been notified and will inspect it today.",
                "change_note": "Assigned to Facilities.",
            },
        )
        self.assertRedirects(response, reverse("complaints:admin_detail", args=[complaint.reference]))
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, Complaint.Status.IN_PROGRESS)
        self.assertEqual(complaint.priority, Complaint.Priority.URGENT)
        self.assertEqual(complaint.status_history.count(), 1)
        event = complaint.status_history.first()
        self.assertEqual(event.previous_status, Complaint.Status.SUBMITTED)
        self.assertEqual(event.new_status, Complaint.Status.IN_PROGRESS)
        self.assertEqual(event.changed_by, self.admin)
        self.assertEqual(event.change_note, "Assigned to Facilities.")

    def test_administrator_search_and_filters(self):
        matching = make_complaint(
            self.student,
            title="East wing Wi-Fi outage",
            category=Complaint.Category.INTERNET,
            priority=Complaint.Priority.URGENT,
            status=Complaint.Status.IN_PROGRESS,
        )
        make_complaint(self.other_student, title="Library table needs repair")
        self.client.login(username="admin", password=PASSWORD)
        response = self.client.get(
            reverse("complaints:admin_list"),
            {
                "q": "Wi-Fi",
                "status": Complaint.Status.IN_PROGRESS,
                "category": Complaint.Category.INTERNET,
                "priority": Complaint.Priority.URGENT,
                "date_from": timezone.localdate().isoformat(),
                "date_to": timezone.localdate().isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, matching.reference)
        self.assertNotContains(response, "Library table needs repair")

    def test_nonexistent_reference_returns_404(self):
        self.client.login(username="student-one", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("complaints:detail", args=["CC-209901-UNKNOWN"])).status_code, 404)

    def test_student_cannot_edit_complaint_after_review_starts(self):
        complaint = make_complaint(self.student, status=Complaint.Status.UNDER_REVIEW)
        self.client.login(username="student-one", password=PASSWORD)
        response = self.client.post(
            reverse("complaints:edit", args=[complaint.reference]),
            {"title": "Tampered title", "description": "A different description.", "category": Complaint.Category.OTHER},
        )
        self.assertRedirects(response, reverse("complaints:detail", args=[complaint.reference]))
        complaint.refresh_from_db()
        self.assertEqual(complaint.title, "Library door is broken")

    def test_staff_profile_role_is_required_for_non_superuser_admin(self):
        staff = User.objects.create_user(username="staff", password=PASSWORD, is_staff=True)
        staff.profile.role = Profile.Role.ADMIN
        staff.profile.save()
        self.client.login(username="staff", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("complaints:admin_dashboard")).status_code, 403)
        staff.user_permissions.add(Permission.objects.get(codename="view_complaint"))
        self.assertEqual(self.client.get(reverse("complaints:admin_dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("complaints:admin_detail", args=[make_complaint(self.student).reference])).status_code, 403)
        staff.user_permissions.add(Permission.objects.get(codename="change_complaint"))
        self.assertEqual(self.client.get(reverse("complaints:admin_detail", args=[make_complaint(self.student).reference])).status_code, 200)
