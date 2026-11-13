from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import StaffProfile, StudentProfile, User

from .helpers import make_faculty, make_group, make_staff, make_student


class RoleConsistencyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FR")
        cls.group = make_group(cls.faculty, "GR")
        cls.student = make_student("stu", cls.group, "REC-1")
        cls.staff = make_staff("stf", cls.faculty)
        cls.superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")

    def test_role_change_with_student_profile_rejected_by_model(self):
        self.student.role = User.Role.STAFF
        with self.assertRaises(ValidationError):
            self.student.full_clean()

    def test_role_change_rejected_in_admin_without_500(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("admin:accounts_user_change", args=[self.student.pk]),
            {
                "username": self.student.username,
                "role": "staff",
                "is_active": "on",
                "date_joined_0": "2026-11-13",
                "date_joined_1": "10:00:00",
                "last_login_0": "",
                "last_login_1": "",
                "first_name": "",
                "last_name": "",
                "email": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("профиль студента", response.content.decode())
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, User.Role.STUDENT)

    def test_make_superuser_with_profile_rejected(self):
        self.student.is_superuser = True
        self.student.is_staff = True
        self.student.role = ""
        with self.assertRaises(ValidationError) as cm:
            self.student.full_clean()
        self.assertIn("профиль", " ".join(cm.exception.messages))

    def test_role_change_without_profile_allowed(self):
        user = User.objects.create_user(username="noprofile", role=User.Role.STUDENT)
        user.role = User.Role.STAFF
        user.full_clean()

    def test_staff_profile_for_student_user_rejected(self):
        profile = StaffProfile(
            user=self.student,
            last_name="X",
            first_name="Y",
            position="Специалист",
            faculty=self.faculty,
        )
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_second_profile_rejected(self):
        sp = StudentProfile(
            user=self.staff,
            last_name="X",
            first_name="Y",
            group=self.group,
            record_number="REC-X",
        )
        with self.assertRaises(ValidationError):
            sp.full_clean()

        student2 = make_student("stu2", self.group, "REC-2")
        StaffProfile.objects.create(
            user=student2,
            last_name="A",
            first_name="B",
            position="Специалист",
            faculty=self.faculty,
        )
        sp2 = StudentProfile(
            user=student2,
            last_name="C",
            first_name="D",
            group=self.group,
            record_number="REC-Y",
        )
        with self.assertRaises(ValidationError) as cm:
            sp2.full_clean()
        self.assertIn("профиль сотрудника", " ".join(cm.exception.messages))

    def test_admin_add_staff_profile_for_student_shows_error(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("admin:accounts_staffprofile_add"),
            {
                "user": self.student.pk,
                "last_name": "X",
                "first_name": "Y",
                "position": "Специалист",
                "faculty": self.faculty.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(StaffProfile.objects.filter(user=self.student).exists())
