import importlib
from datetime import date

import django.apps
from django.test import TestCase

from accounts.demo import seed_demo_data
from core.testing import FrozenClockMixin
from schedule.demo import seed_schedule_demo
from schedule.models import LessonChange, WeeklyLesson
from schedule.mutations import save_lesson_change, save_weekly_lesson
from university.models import Discipline, Room, StudyGroup, Teacher


class DemoMarkerTests(FrozenClockMixin, TestCase):
    def _seed(self, today: date = date(2026, 11, 18)):
        seed_demo_data("Demo-Pass-2026-test!")
        return seed_schedule_demo(today)

    def test_seed_marks_rows(self):
        self._seed()
        self.assertEqual(WeeklyLesson.objects.exclude(seed_key="").count(), 18)
        self.assertEqual(LessonChange.objects.exclude(seed_key="").count(), 8)
        keys = list(WeeklyLesson.objects.exclude(seed_key="").values_list("seed_key", flat=True))
        self.assertEqual(len(set(keys)), 18)
        change_keys = list(
            LessonChange.objects.exclude(seed_key="").values_list("seed_key", flat=True)
        )
        self.assertEqual(len(set(change_keys)), 8)

    def test_admin_lesson_with_same_old_key_survives_reseed(self):
        self._seed()
        discipline = Discipline.objects.get(name="Введение в цифровую дипломатию")
        group = StudyGroup.objects.get(name="ЦД-101")
        room402 = Room.objects.get(code="room-402")
        teacher = Teacher.objects.get(last_name="Лебедев")
        admin_lesson = WeeklyLesson(
            weekday=0,
            slot=1,
            discipline=discipline,
            lesson_type="lecture",
            teacher=teacher,
            room=room402,
            valid_from=date(2028, 1, 1),
            valid_until=date(2028, 6, 30),
        )
        save_weekly_lesson(admin_lesson, [group])

        self._seed()
        self._seed()
        admin_lesson.refresh_from_db()
        self.assertEqual(admin_lesson.seed_key, "")
        self.assertEqual(admin_lesson.room, room402)
        self.assertEqual(admin_lesson.valid_from, date(2028, 1, 1))
        self.assertEqual(admin_lesson.valid_until, date(2028, 6, 30))
        self.assertEqual(list(admin_lesson.groups.values_list("name", flat=True)), ["ЦД-101"])
        self.assertEqual(WeeklyLesson.objects.exclude(seed_key="").count(), 18)

    def test_admin_change_survives_reseed(self):
        self._seed()
        discipline = Discipline.objects.get(name="Введение в цифровую дипломатию")
        group = StudyGroup.objects.get(name="ЦД-101")
        room402 = Room.objects.get(code="room-402")
        teacher = Teacher.objects.get(last_name="Лебедев")
        admin_lesson = WeeklyLesson(
            weekday=0,
            slot=1,
            discipline=discipline,
            lesson_type="lecture",
            teacher=teacher,
            room=room402,
            valid_from=date(2028, 1, 1),
            valid_until=date(2028, 6, 30),
        )
        save_weekly_lesson(admin_lesson, [group])
        admin_change = LessonChange(
            weekly_lesson=admin_lesson,
            original_date=date(2028, 1, 3),
            kind="cancelled",
            reason="Причина",
        )
        save_lesson_change(admin_change)

        self._seed()
        self.assertEqual(LessonChange.objects.filter(weekly_lesson=admin_lesson).count(), 1)
        self.assertEqual(LessonChange.objects.get(weekly_lesson=admin_lesson).seed_key, "")

    def test_data_migration_marks_legacy_rows(self):
        self._seed()
        WeeklyLesson.objects.update(seed_key="")
        LessonChange.objects.update(seed_key="")

        discipline = Discipline.objects.get(name="Введение в цифровую дипломатию")
        group = StudyGroup.objects.get(name="ЦД-101")
        room402 = Room.objects.get(code="room-402")
        teacher = Teacher.objects.get(last_name="Лебедев")
        admin_lesson = WeeklyLesson(
            weekday=0,
            slot=1,
            discipline=discipline,
            lesson_type="lecture",
            teacher=teacher,
            room=room402,
            valid_from=date(2028, 1, 1),
            valid_until=date(2028, 6, 30),
        )
        save_weekly_lesson(admin_lesson, [group])

        mod = importlib.import_module("schedule.migrations.0003_mark_existing_demo_rows")
        mod.mark_existing_demo_rows(django.apps.apps, None)
        self.assertEqual(WeeklyLesson.objects.exclude(seed_key="").count(), 18)
        self.assertEqual(LessonChange.objects.exclude(seed_key="").count(), 8)
        admin_lesson.refresh_from_db()
        self.assertEqual(admin_lesson.seed_key, "")

        mod.mark_existing_demo_rows(django.apps.apps, None)
        self.assertEqual(WeeklyLesson.objects.exclude(seed_key="").count(), 18)
        self.assertEqual(LessonChange.objects.exclude(seed_key="").count(), 8)

    def test_reseed_after_migration_no_duplicates(self):
        self._seed()
        WeeklyLesson.objects.update(seed_key="")
        LessonChange.objects.update(seed_key="")
        mod = importlib.import_module("schedule.migrations.0003_mark_existing_demo_rows")
        mod.mark_existing_demo_rows(django.apps.apps, None)

        self._seed()
        self.assertEqual(WeeklyLesson.objects.exclude(seed_key="").count(), 18)
        self.assertEqual(LessonChange.objects.exclude(seed_key="").count(), 8)
        self.assertEqual(WeeklyLesson.objects.count(), 18)
