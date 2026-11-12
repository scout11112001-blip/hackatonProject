from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import StudentProfile, User

from .helpers import make_faculty, make_group, make_staff, make_student


class UserModelTests(TestCase):
    def test_user_without_role_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user("x")

    def test_superuser_with_role_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_superuser("x", role="student")

    def test_non_superuser_cannot_be_admin_staff(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user("x", role="staff", is_staff=True)

    def test_createsuperuser_path_works(self):
        root = User.objects.create_superuser("root", password=None)
        self.assertEqual(root.role, "")
        self.assertTrue(root.is_superuser)
        self.assertTrue(root.is_staff)

    def test_role_properties(self):
        student = User.objects.create_user("s", role="student")
        staff = User.objects.create_user("t", role="staff")
        self.assertTrue(student.is_student)
        self.assertFalse(student.is_deanery_staff)
        self.assertTrue(staff.is_deanery_staff)
        self.assertFalse(staff.is_student)


class StudentProfileModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FF")
        cls.group = make_group(cls.faculty, "GG", course=3)
        cls.student = make_student("stu", cls.group, "REC-1")
        cls.profile = cls.student.student_profile

    def test_student_profile_derived_fields(self):
        self.assertEqual(self.profile.faculty, self.faculty)
        self.assertEqual(self.profile.program, self.group.program)
        self.assertEqual(self.profile.course, 3)
        self.assertEqual(self.profile.full_name, "stu-last stu-first")
        self.assertNotIn("  ", self.profile.full_name)

    def test_profile_role_validated_by_full_clean(self):
        staff = make_staff("stf", self.faculty)
        profile = StudentProfile(
            user=staff,
            last_name="X",
            first_name="Y",
            group=self.group,
            record_number="REC-2",
        )
        with self.assertRaises(ValidationError):
            profile.full_clean()
