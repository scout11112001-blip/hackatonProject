from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .helpers import make_faculty, make_group, make_staff, make_student


class AdminAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FA")
        cls.group = make_group(cls.faculty, "GA")
        cls.student = make_student("stu", cls.group, "REC-1")
        cls.staff = make_staff("stf", cls.faculty)
        cls.superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")

    def test_student_and_staff_cannot_open_admin(self):
        for user in (self.student, self.staff):
            self.client.force_login(user)
            response = self.client.get(reverse("admin:index"))
            self.assertEqual(response.status_code, 302)

    def test_superuser_can_open_admin(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)

    def test_admin_user_add_form_has_role(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:accounts_user_add"))
        self.assertEqual(response.status_code, 200)
        self.assertIn('name="role"', response.content.decode())

    def test_admin_user_add_without_role_shows_error(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("admin:accounts_user_add"),
            {"username": "newu", "role": "", "usable_password": "false"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newu").exists())
