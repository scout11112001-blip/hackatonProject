import os
import time
from datetime import date
from unittest import mock, skipUnless

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from academics.models import Attendance, CurrentMark, FinalResult
from academics.services import validate_occurrence_for_student
from accounts.tests.helpers import make_faculty, make_group, make_student
from core.testing import FrozenClockMixin, moscow
from schedule.tests.helpers import make_discipline, make_lesson, make_room

from .helpers import make_attendance, make_item, make_mark, make_result, make_term


class MoscowMidnightTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "G1")
        cls.student = make_student("sa", cls.group, "REC-A")
        cls.profile = cls.student.student_profile
        cls.room = make_room("room-101")
        cls.room2 = make_room("room-102")
        cls.discipline = make_discipline("Дисциплина")

    def _make_item(self):
        return make_item(self.group, self.discipline, make_term())

    def test_mark_future_check(self):
        item = self._make_item()
        with mock.patch("django.utils.timezone.now", return_value=moscow("2026-11-17 23:59:59")):
            with self.assertRaises(ValidationError) as cm:
                make_mark(self.profile, item, 5, date(2026, 11, 18))
            self.assertIn("в будущем", " ".join(cm.exception.messages))
        with mock.patch("django.utils.timezone.now", return_value=moscow("2026-11-18 00:00:00")):
            make_mark(self.profile, item, 5, date(2026, 11, 18))

    def test_final_result_future_check(self):
        item = self._make_item()
        with mock.patch("django.utils.timezone.now", return_value=moscow("2026-11-17 23:59:59")):
            with self.assertRaises(ValidationError) as cm:
                make_result(self.profile, item, "5", date=date(2026, 11, 18))
            self.assertIn("в будущем", " ".join(cm.exception.messages))
        with mock.patch("django.utils.timezone.now", return_value=moscow("2026-11-18 00:00:00")):
            make_result(self.profile, item, "5", date=date(2026, 11, 18))

    def test_attendance_today_check(self):
        lesson = make_lesson(
            [self.group], weekday=2, slot=2, room=self.room, discipline=self.discipline
        )
        with mock.patch("django.utils.timezone.now", return_value=moscow("2026-11-17 23:59:59")):
            with self.assertRaises(ValidationError) as cm:
                make_attendance(self.profile, lesson, date(2026, 11, 18), "present")
            self.assertIn("будущего", " ".join(cm.exception.messages))
        with mock.patch("django.utils.timezone.now", return_value=moscow("2026-11-18 00:00:00")):
            make_attendance(self.profile, lesson, date(2026, 11, 18), "present")

    def test_today_view_date(self):
        self.client.force_login(self.student)
        with mock.patch("django.utils.timezone.now", return_value=moscow("2026-11-17 23:59:59")):
            response = self.client.get(reverse("schedule:today"))
            self.assertEqual(response.context["day"].date, date(2026, 11, 17))
        with mock.patch("django.utils.timezone.now", return_value=moscow("2026-11-18 00:00:00")):
            response = self.client.get(reverse("schedule:today"))
            self.assertEqual(response.context["day"].date, date(2026, 11, 18))

    def test_unmarked_counter_switches_at_midnight(self):
        self._make_item()
        make_lesson([self.group], weekday=1, slot=2, room=self.room, discipline=self.discipline)
        self.client.force_login(self.student)
        with mock.patch("django.utils.timezone.now", return_value=moscow("2026-11-17 23:59:59")):
            response = self.client.get(reverse("academics:my_grades"))
            before = sum(d.attendance.unmarked for d in response.context["report"].disciplines)
        with mock.patch("django.utils.timezone.now", return_value=moscow("2026-11-18 00:00:00")):
            response = self.client.get(reverse("academics:my_grades"))
            after = sum(d.attendance.unmarked for d in response.context["report"].disciplines)
        self.assertEqual(after, before + 1)

    @skipUnless(hasattr(time, "tzset"), "requires time.tzset")
    def test_machine_timezone_does_not_matter(self):
        self.client.force_login(self.student)
        with mock.patch.dict(os.environ, {"TZ": "America/Los_Angeles"}):
            time.tzset()
            try:
                with mock.patch(
                    "django.utils.timezone.now", return_value=moscow("2026-11-18 00:00:00")
                ):
                    response = self.client.get(reverse("schedule:today"))
                    self.assertEqual(response.context["day"].date, date(2026, 11, 18))
            finally:
                time.tzset()

    def test_seed_at_midnight(self):
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": "Demo-Pass-2026-test!"}):
            with mock.patch(
                "django.utils.timezone.now", return_value=moscow("2026-11-17 23:59:59")
            ):
                call_command("seed_demo")
            with mock.patch(
                "django.utils.timezone.now", return_value=moscow("2026-11-18 00:00:00")
            ):
                call_command("seed_demo")
        today = date(2026, 11, 18)
        for a in Attendance.objects.all():
            self.assertEqual(
                validate_occurrence_for_student(a.student, a.weekly_lesson, a.original_date, today),
                [],
            )
        self.assertFalse(CurrentMark.objects.filter(date__gt=today).exists())
        self.assertFalse(FinalResult.objects.filter(date__gt=today).exists())
