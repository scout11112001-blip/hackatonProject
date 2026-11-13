from datetime import date
from unittest import mock

from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext

from accounts.tests.helpers import make_faculty, make_group
from schedule.forms import WeeklyLessonAdminForm
from schedule.locking import lock_rooms_and_groups
from schedule.models import ChangeKind, LessonChange, WeeklyLesson
from schedule.mutations import save_lesson_change, save_weekly_lesson

from .helpers import make_discipline, make_lesson, make_room, make_teacher


class LockingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group_1 = make_group(cls.faculty, "G1")
        cls.group_2 = make_group(cls.faculty, "G2")
        cls.room = make_room("room-101")
        cls.room2 = make_room("room-205", floor=2)
        cls.discipline = make_discipline("Дисциплина")
        cls.teacher = make_teacher("Лебедев")

    def test_save_weekly_lesson_locks_room_and_groups(self):
        lesson = WeeklyLesson(
            weekday=0,
            slot=1,
            discipline=self.discipline,
            lesson_type="lecture",
            teacher=self.teacher,
            room=self.room,
            valid_from=date(2026, 9, 1),
            valid_until=date(2026, 12, 31),
        )
        with mock.patch("schedule.locking.lock_rooms_and_groups", wraps=lock_rooms_and_groups) as m:
            save_weekly_lesson(lesson, [self.group_2, self.group_1])
        m.assert_called_once()
        args, _ = m.call_args
        self.assertEqual(args[0], [self.room.pk])
        self.assertEqual(set(args[1]), {self.group_1.pk, self.group_2.pk})

    def test_change_locks_target_room(self):
        lesson = make_lesson([self.group_1], weekday=0, slot=1, room=self.room)
        change = LessonChange(
            weekly_lesson=lesson,
            original_date=date(2026, 11, 16),
            kind=ChangeKind.MOVED,
            new_date=date(2026, 11, 19),
            new_slot=5,
            new_room=self.room2,
            reason="Перенос",
        )
        with mock.patch("schedule.locking.lock_rooms_and_groups", wraps=lock_rooms_and_groups) as m:
            save_lesson_change(change)
        m.assert_called_once()
        args, _ = m.call_args
        self.assertEqual(args[0], [self.room2.pk])
        self.assertEqual(set(args[1]), {self.group_1.pk})

    def test_lock_queries_issued(self):
        with transaction.atomic():
            with CaptureQueriesContext(connection) as ctx:
                lock_rooms_and_groups(
                    [self.room2.pk, self.room.pk, None], [self.group_2.pk, self.group_1.pk]
                )
        queries = [q["sql"] for q in ctx.captured_queries]
        self.assertEqual(len(queries), 2)
        self.assertIn("university_room", queries[0])
        self.assertIn("university_studygroup", queries[1])
        if connection.features.has_select_for_update:
            self.assertIn("FOR UPDATE", queries[0])
            self.assertIn("FOR UPDATE", queries[1])

    def test_admin_form_locks(self):
        data = {
            "weekday": 0,
            "slot": 1,
            "discipline": self.discipline.pk,
            "lesson_type": "lecture",
            "teacher": self.teacher.pk,
            "room": self.room.pk,
            "groups": [self.group_1.pk],
            "valid_from": "2026-09-01",
            "valid_until": "2026-12-31",
        }
        with transaction.atomic():
            with mock.patch(
                "schedule.locking.lock_rooms_and_groups", wraps=lock_rooms_and_groups
            ) as m:
                form = WeeklyLessonAdminForm(data=data)
                form.is_valid()
        m.assert_called()


class NoLockOutsideAtomicTests(TransactionTestCase):
    def test_no_lock_outside_atomic(self):
        faculty = make_faculty("FO")
        group = make_group(faculty, "GO")
        room = make_room("room-700")
        with CaptureQueriesContext(connection) as ctx:
            lock_rooms_and_groups([room.pk], [group.pk])
        self.assertEqual(len(ctx.captured_queries), 0)
