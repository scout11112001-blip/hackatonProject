import os
from datetime import date
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from accounts.demo import seed_demo_data
from core.testing import FrozenClockMixin
from schedule.demo import seed_schedule_demo
from schedule.models import ChangeKind, LessonChange, WeeklyLesson
from schedule.services import week_schedule
from schedule.validation import validate_weekly_lesson
from university.models import Discipline, Room, StudyGroup, Teacher

from .helpers import aware


class ScheduleDemoTests(FrozenClockMixin, TestCase):
    def _seed(self, today: date):
        seed_demo_data("Demo-Pass-2026-test!")
        return seed_schedule_demo(today)

    def test_counts(self):
        summary = self._seed(date(2026, 11, 18))
        self.assertEqual(summary.rooms, 7)
        self.assertEqual(summary.teachers, 6)
        self.assertEqual(summary.disciplines, 6)
        self.assertEqual(summary.weekly_lessons, 18)
        self.assertEqual(summary.changes, 8)
        self.assertEqual(Room.objects.count(), 7)
        self.assertEqual(Teacher.objects.count(), 6)
        self.assertEqual(Discipline.objects.count(), 6)
        self.assertEqual(WeeklyLesson.objects.count(), 18)
        self.assertEqual(LessonChange.objects.count(), 8)
        for kind in (
            ChangeKind.CANCELLED,
            ChangeKind.MOVED,
            ChangeKind.ROOM_CHANGED,
            ChangeKind.TEACHER_REPLACED,
        ):
            self.assertEqual(LessonChange.objects.filter(kind=kind).count(), 2)
        self.assertGreaterEqual(Room.objects.values_list("floor", flat=True).distinct().count(), 3)

    def test_change_dates_in_current_and_next_week(self):
        self._seed(date(2026, 11, 18))
        for change in LessonChange.objects.all():
            self.assertGreaterEqual(change.original_date, date(2026, 11, 16))
            self.assertLessEqual(change.original_date, date(2026, 11, 29))

    def test_idempotent(self):
        self._seed(date(2026, 11, 18))
        self._seed(date(2026, 11, 18))
        self.assertEqual(WeeklyLesson.objects.count(), 18)
        self.assertEqual(LessonChange.objects.count(), 8)
        self.assertEqual(Room.objects.count(), 7)

    def test_rerun_later_refreshes_changes(self):
        self._seed(date(2026, 11, 18))
        self._seed(date(2026, 12, 2))
        self.assertEqual(WeeklyLesson.objects.count(), 18)
        self.assertEqual(LessonChange.objects.count(), 8)
        for change in LessonChange.objects.all():
            self.assertGreaterEqual(change.original_date, date(2026, 11, 30))
            self.assertLessEqual(change.original_date, date(2026, 12, 13))

    def test_rerun_months_later_refreshes_changes(self):
        self._seed(date(2026, 11, 18))
        self._seed(date(2027, 3, 1))
        self.assertEqual(WeeklyLesson.objects.count(), 18)
        self.assertEqual(LessonChange.objects.count(), 8)
        for change in LessonChange.objects.all():
            self.assertGreaterEqual(change.original_date, date(2027, 3, 1))
            self.assertLessEqual(change.original_date, date(2027, 3, 14))

    def test_far_date_renders_without_reseed(self):
        self._seed(date(2026, 11, 18))
        group = StudyGroup.objects.get(name="ЦД-101")
        week = week_schedule(date(2026, 12, 2), [group.pk], today=date(2026, 12, 2))
        for day in week.days[:5]:  # Monday..Friday
            self.assertTrue(day.items, f"no items on {day.date}")
        week2 = week_schedule(date(2026, 11, 28), [group.pk], today=date(2026, 11, 28))
        self.assertEqual(len(week2.days), 7)

    def test_seeded_schedule_has_no_conflicts(self):
        self._seed(date(2026, 11, 18))
        for lesson in WeeklyLesson.objects.all():
            errors = validate_weekly_lesson(
                weekday=lesson.weekday,
                slot=lesson.slot,
                valid_from=lesson.valid_from,
                valid_until=lesson.valid_until,
                room_id=lesson.room_id,
                group_ids=list(lesson.groups.values_list("id", flat=True)),
                exclude_pk=lesson.pk,
            )
            self.assertEqual(errors, [], f"conflicts for lesson {lesson}")

    def test_command_output_and_idempotency(self):
        with (
            mock.patch.dict(os.environ, {"DEMO_PASSWORD": "Demo-Pass-2026-test!"}),
            mock.patch("django.utils.timezone.now", return_value=aware("2026-11-18 10:00")),
        ):
            out = StringIO()
            call_command("seed_demo", stdout=out)
            self.assertIn("Schedule ready", out.getvalue())
            lessons = WeeklyLesson.objects.count()
            changes = LessonChange.objects.count()
            out2 = StringIO()
            call_command("seed_demo", stdout=out2)
            self.assertIn("Schedule ready", out2.getvalue())
            self.assertEqual(WeeklyLesson.objects.count(), lessons)
            self.assertEqual(LessonChange.objects.count(), changes)
