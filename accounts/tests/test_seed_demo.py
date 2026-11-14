import os
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounts.models import StaffProfile, StudentProfile, User
from core.testing import FrozenClockMixin
from university.models import Faculty, Program, StudyGroup

from .helpers import make_faculty, make_group, make_student


class SeedDemoTests(FrozenClockMixin, TestCase):
    def test_creates_expected_data(self):
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": "Demo-Pass-2026-test!"}):
            call_command("seed_demo")
        self.assertEqual(Faculty.objects.count(), 2)
        self.assertEqual(Program.objects.count(), 2)
        self.assertEqual(StudyGroup.objects.count(), 2)
        self.assertEqual(StudentProfile.objects.count(), 3)
        self.assertEqual(StaffProfile.objects.count(), 2)
        student1 = User.objects.get(username="student1")
        staff1 = User.objects.get(username="staff1")
        self.assertEqual(student1.role, User.Role.STUDENT)
        self.assertEqual(staff1.role, User.Role.STAFF)
        self.assertFalse(User.objects.filter(is_staff=True).exists())

    def test_idempotent(self):
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": "Demo-Pass-2026-test!"}):
            call_command("seed_demo")
            call_command("seed_demo")
        self.assertEqual(Faculty.objects.count(), 2)
        self.assertEqual(Program.objects.count(), 2)
        self.assertEqual(StudyGroup.objects.count(), 2)
        self.assertEqual(StudentProfile.objects.count(), 3)
        self.assertEqual(StaffProfile.objects.count(), 2)
        self.assertEqual(User.objects.count(), 5)
        self.assertTrue(
            User.objects.get(username="student1").check_password("Demo-Pass-2026-test!")
        )

    def test_passwords_hashed(self):
        password = "Demo-Pass-2026-test!"
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": password}):
            call_command("seed_demo")
        for user in User.objects.all():
            self.assertNotEqual(user.password, password)
            self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
            self.assertTrue(user.check_password(password))

    def test_missing_password_fails(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("DEMO_PASSWORD", None)
            with self.assertRaisesMessage(CommandError, "DEMO_PASSWORD"):
                call_command("seed_demo")
        self.assertEqual(User.objects.count(), 0)

    def test_weak_password_fails(self):
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": "123"}):
            with self.assertRaisesMessage(CommandError, "too weak"):
                call_command("seed_demo")
        self.assertEqual(User.objects.count(), 0)

    def test_conflicting_existing_user_fails(self):
        User.objects.create_user("student1", role="staff")
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": "Demo-Pass-2026-test!"}):
            with self.assertRaises(CommandError):
                call_command("seed_demo")
        self.assertEqual(User.objects.get(username="student1").role, User.Role.STAFF)

    def test_password_not_printed(self):
        password = "Demo-Pass-2026-test!"
        out = StringIO()
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": password}):
            call_command("seed_demo", stdout=out)
        self.assertNotIn(password, out.getvalue())

    def test_record_number_collision_fails_cleanly(self):
        faculty = make_faculty("FF")
        group = make_group(faculty, "GG")
        make_student("other", group, "ST-2026-0001")
        users_before = User.objects.count()
        faculties_before = Faculty.objects.count()
        groups_before = StudyGroup.objects.count()
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": "Demo-Pass-2026-test!"}):
            with self.assertRaisesMessage(CommandError, "ST-2026-0001"):
                call_command("seed_demo")
        self.assertEqual(User.objects.count(), users_before)
        self.assertEqual(Faculty.objects.count(), faculties_before)
        self.assertEqual(StudyGroup.objects.count(), groups_before)
        self.assertFalse(User.objects.filter(username="student1").exists())
