from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.tests.helpers import make_faculty, make_group
from core.testing import FrozenClockMixin
from schedule.forms import WeeklyLessonAdminForm
from schedule.models import ChangeKind, LessonChange, WeeklyLesson
from schedule.mutations import save_lesson_change, save_weekly_lesson

from .helpers import make_discipline, make_lesson, make_room, make_teacher


class RevalidationTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FR")
        cls.g1 = make_group(cls.faculty, "G1")
        cls.g2 = make_group(cls.faculty, "G2")
        cls.g3 = make_group(cls.faculty, "G3")
        cls.g4 = make_group(cls.faculty, "G4")
        cls.g9 = make_group(cls.faculty, "G9")
        cls.r1 = make_room("room-101")
        cls.r2 = make_room("room-102")
        cls.r3 = make_room("room-103")
        cls.r4 = make_room("room-104")
        cls.r5 = make_room("room-105")

    def test_slot_change_hits_moved_in_room(self):
        l1 = make_lesson([self.g1], weekday=0, slot=2, room=self.r1)
        l2 = make_lesson([self.g2], weekday=1, slot=1, room=self.r2)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l2,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 23),
                new_slot=3,
                new_room=self.r1,
                reason="Перенос",
            )
        )
        l1.slot = 3
        with self.assertRaises(ValidationError) as cm:
            save_weekly_lesson(l1, [self.g1])
        self.assertIn("23.11.2026", " ".join(cm.exception.messages))

    def test_room_change_hits_room_changed_occurrence(self):
        l1 = make_lesson([self.g1], weekday=0, slot=2, room=self.r1)
        l3 = make_lesson([self.g3], weekday=0, slot=2, room=self.r3)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l3,
                original_date=date(2026, 11, 23),
                kind=ChangeKind.ROOM_CHANGED,
                new_room=self.r4,
                reason="Замена",
            )
        )
        l1.room = self.r4
        with self.assertRaises(ValidationError) as cm:
            save_weekly_lesson(l1, [self.g1])
        self.assertIn("23.11.2026", " ".join(cm.exception.messages))

    def test_own_move_target_conflicts_after_room_change(self):
        l1 = make_lesson([self.g1], weekday=0, slot=2, room=self.r1)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l1,
                original_date=date(2026, 11, 23),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 25),
                new_slot=4,
                reason="Перенос",
            )
        )
        make_lesson([self.g4], weekday=2, slot=4, room=self.r2)
        l1.room = self.r2
        with self.assertRaises(ValidationError) as cm:
            save_weekly_lesson(l1, [self.g1])
        self.assertIn("25.11.2026", " ".join(cm.exception.messages))

    def test_own_room_change_equals_new_room(self):
        l1 = make_lesson([self.g1], weekday=0, slot=2, room=self.r1)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l1,
                original_date=date(2026, 11, 23),
                kind=ChangeKind.ROOM_CHANGED,
                new_room=self.r2,
                reason="Замена",
            )
        )
        l1.room = self.r2
        with self.assertRaises(ValidationError) as cm:
            save_weekly_lesson(l1, [self.g1])
        self.assertIn("совпадает", " ".join(cm.exception.messages))

    def test_group_change_hits_moved_in_group(self):
        l5 = make_lesson([self.g2], weekday=3, slot=1, room=self.r5)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l5,
                original_date=date(2026, 11, 19),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 23),
                new_slot=2,
                reason="Перенос",
            )
        )
        l1 = make_lesson([self.g1], weekday=0, slot=2, room=self.r1)
        with self.assertRaises(ValidationError) as cm:
            save_weekly_lesson(l1, [self.g1, self.g2])
        messages = " ".join(cm.exception.messages)
        self.assertIn("23.11.2026", messages)
        self.assertIn("G2", messages)

    def test_cancelled_own_occurrence_frees_date(self):
        l1 = make_lesson([self.g1], weekday=0, slot=2, room=self.r1)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l1,
                original_date=date(2026, 11, 23),
                kind=ChangeKind.CANCELLED,
                reason="Отмена",
            )
        )
        l2 = make_lesson([self.g2], weekday=1, slot=1, room=self.r2)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l2,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 23),
                new_slot=3,
                new_room=self.r1,
                reason="Перенос",
            )
        )
        l1.slot = 3
        save_weekly_lesson(l1, [self.g1])

    def test_new_lesson_where_other_was_moved_in(self):
        l2 = make_lesson([self.g2], weekday=1, slot=1, room=self.r2)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l2,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 23),
                new_slot=3,
                new_room=self.r1,
                reason="Перенос",
            )
        )
        new_lesson = WeeklyLesson(
            weekday=0,
            slot=3,
            discipline=make_discipline("Новая дисциплина"),
            lesson_type="lecture",
            teacher=make_teacher("Новый преподаватель"),
            room=self.r1,
            valid_from=date(2026, 9, 1),
            valid_until=date(2026, 12, 31),
        )
        with self.assertRaises(ValidationError) as cm:
            save_weekly_lesson(new_lesson, [self.g9])
        self.assertIn("23.11.2026", " ".join(cm.exception.messages))

    def test_admin_form_reports_revalidation_error(self):
        l1 = make_lesson([self.g1], weekday=0, slot=2, room=self.r1)
        l2 = make_lesson([self.g2], weekday=1, slot=1, room=self.r2)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l2,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 23),
                new_slot=3,
                new_room=self.r1,
                reason="Перенос",
            )
        )
        data = {
            "weekday": 0,
            "slot": 3,
            "discipline": l1.discipline_id,
            "lesson_type": l1.lesson_type,
            "teacher": l1.teacher_id,
            "room": self.r1.pk,
            "groups": [self.g1.pk],
            "valid_from": "2026-09-01",
            "valid_until": "2026-12-31",
        }
        form = WeeklyLessonAdminForm(instance=l1, data=data)
        self.assertFalse(form.is_valid())
        self.assertTrue(any("23.11.2026" in e for e in form.non_field_errors()))

    def test_message_limit(self):
        l1 = make_lesson([self.g1], weekday=0, slot=2, room=self.r1)
        o = make_lesson([self.g2], weekday=0, slot=3, room=self.r2)
        mondays = [date(2026, 9, 7) + timedelta(weeks=i) for i in range(12)]
        for d in mondays:
            save_lesson_change(
                LessonChange(
                    weekly_lesson=o,
                    original_date=d,
                    kind=ChangeKind.ROOM_CHANGED,
                    new_room=self.r1,
                    reason="Замена",
                )
            )
        l1.slot = 3
        with self.assertRaises(ValidationError) as cm:
            save_weekly_lesson(l1, [self.g1])
        messages = cm.exception.messages
        self.assertEqual(len(messages), 11)
        self.assertTrue(messages[-1].startswith("…и ещё"))
