from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.tests.helpers import make_faculty, make_group
from core.testing import FrozenClockMixin
from schedule.forms import WeeklyLessonAdminForm
from schedule.models import ChangeKind, LessonChange, WeeklyLesson
from schedule.mutations import save_lesson_change, save_weekly_lesson

from .helpers import make_discipline, make_lesson, make_room, make_teacher


class ValidationFixture(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group_a = make_group(cls.faculty, "GA")
        cls.group_b = make_group(cls.faculty, "GB")
        cls.group_c = make_group(cls.faculty, "GC")
        cls.room = make_room("room-101")
        cls.room2 = make_room("room-205", floor=2)
        cls.teacher = make_teacher("Лебедев")
        cls.teacher2 = make_teacher("Воронцова")
        cls.discipline = make_discipline("Математика")


class WeeklyLessonValidationTests(ValidationFixture):
    def test_group_overlap_rejected(self):
        make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        with self.assertRaises(ValidationError) as cm:
            make_lesson([self.group_a], weekday=0, slot=1, room=self.room2)
        self.assertIn("GA", " ".join(cm.exception.messages))

    def test_room_overlap_rejected(self):
        make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        with self.assertRaises(ValidationError) as cm:
            make_lesson([self.group_b], weekday=0, slot=1, room=self.room)
        self.assertIn("101", " ".join(cm.exception.messages))

    def test_partial_group_overlap_rejected(self):
        make_lesson([self.group_a, self.group_b], weekday=0, slot=1, room=self.room)
        with self.assertRaises(ValidationError) as cm:
            make_lesson([self.group_b, self.group_c], weekday=0, slot=1, room=self.room2)
        messages = " ".join(cm.exception.messages)
        self.assertIn("GB", messages)
        self.assertNotIn("GA", messages)

    def test_non_overlapping_ranges_allowed(self):
        make_lesson(
            [self.group_a],
            weekday=0,
            slot=1,
            room=self.room,
            valid_from=date(2026, 9, 1),
            valid_until=date(2026, 10, 31),
        )
        make_lesson(
            [self.group_a],
            weekday=0,
            slot=1,
            room=self.room,
            valid_from=date(2026, 11, 1),
            valid_until=date(2026, 12, 31),
        )

    def test_adjacent_inclusive_range_conflicts(self):
        make_lesson(
            [self.group_a],
            weekday=0,
            slot=1,
            room=self.room,
            valid_from=date(2026, 9, 1),
            valid_until=date(2026, 10, 31),
        )
        with self.assertRaises(ValidationError):
            make_lesson(
                [self.group_a],
                weekday=0,
                slot=1,
                room=self.room2,
                valid_from=date(2026, 10, 31),
                valid_until=date(2026, 12, 31),
            )

    def test_editing_lesson_does_not_conflict_with_itself(self):
        lesson = make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        lesson.discipline = self.discipline
        save_weekly_lesson(lesson, [self.group_a])

    def test_empty_groups_rejected(self):
        with self.assertRaises(ValidationError):
            save_weekly_lesson(
                WeeklyLesson(
                    weekday=0,
                    slot=1,
                    discipline=self.discipline,
                    lesson_type="lecture",
                    teacher=self.teacher,
                    room=self.room,
                    valid_from=date(2026, 9, 1),
                    valid_until=date(2026, 12, 31),
                ),
                [],
            )

    def test_weekday_edit_with_existing_change_rejected(self):
        lesson = make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="Отмена",
            )
        )
        lesson.weekday = 1
        with self.assertRaises(ValidationError) as cm:
            save_weekly_lesson(lesson, [self.group_a])
        self.assertIn("изменение", " ".join(cm.exception.messages))

    def test_invalid_range_rejected(self):
        with self.assertRaises(ValidationError):
            save_weekly_lesson(
                WeeklyLesson(
                    weekday=0,
                    slot=1,
                    discipline=self.discipline,
                    lesson_type="lecture",
                    teacher=self.teacher,
                    room=self.room,
                    valid_from=date(2026, 12, 31),
                    valid_until=date(2026, 9, 1),
                ),
                [self.group_a],
            )

    def test_admin_form_rejects_group_overlap(self):
        make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        form = WeeklyLessonAdminForm(
            data={
                "weekday": 0,
                "slot": 1,
                "discipline": self.discipline.pk,
                "lesson_type": "lecture",
                "teacher": self.teacher.pk,
                "room": self.room2.pk,
                "groups": [self.group_a.pk],
                "valid_from": "2026-09-01",
                "valid_until": "2026-12-31",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())


class LessonChangeRuleTests(ValidationFixture):
    def _lesson(self, weekday=0):
        return make_lesson(
            [self.group_a], weekday=weekday, slot=1, room=self.room, teacher=self.teacher
        )

    def test_weekday_mismatch(self):
        lesson = self._lesson(weekday=0)
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(
                LessonChange(
                    weekly_lesson=lesson,
                    original_date=date(2026, 11, 17),
                    kind=ChangeKind.CANCELLED,
                    reason="x",
                )
            )
        self.assertIn("original_date", cm.exception.message_dict)

    def test_date_out_of_range(self):
        lesson = self._lesson(weekday=0)
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(
                LessonChange(
                    weekly_lesson=lesson,
                    original_date=date(2026, 1, 5),
                    kind=ChangeKind.CANCELLED,
                    reason="x",
                )
            )
        self.assertIn("original_date", cm.exception.message_dict)

    def test_moved_without_new_date(self):
        lesson = self._lesson(weekday=0)
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(
                LessonChange(
                    weekly_lesson=lesson,
                    original_date=date(2026, 11, 16),
                    kind=ChangeKind.MOVED,
                    new_slot=5,
                    reason="x",
                )
            )
        self.assertIn("new_date", cm.exception.message_dict)

    def test_cancelled_with_new_room(self):
        lesson = self._lesson(weekday=0)
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(
                LessonChange(
                    weekly_lesson=lesson,
                    original_date=date(2026, 11, 16),
                    kind=ChangeKind.CANCELLED,
                    new_room=self.room2,
                    reason="x",
                )
            )
        self.assertIn("new_room", cm.exception.message_dict)

    def test_room_changed_same_room(self):
        lesson = self._lesson(weekday=0)
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(
                LessonChange(
                    weekly_lesson=lesson,
                    original_date=date(2026, 11, 16),
                    kind=ChangeKind.ROOM_CHANGED,
                    new_room=self.room,
                    reason="x",
                )
            )
        self.assertIn("new_room", cm.exception.message_dict)

    def test_teacher_replaced_same_teacher(self):
        lesson = self._lesson(weekday=0)
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(
                LessonChange(
                    weekly_lesson=lesson,
                    original_date=date(2026, 11, 16),
                    kind=ChangeKind.TEACHER_REPLACED,
                    new_teacher=self.teacher,
                    reason="x",
                )
            )
        self.assertIn("new_teacher", cm.exception.message_dict)

    # TASK-013: the reason is optional now (AC13).
    def test_blank_reason_allowed(self):
        lesson = self._lesson(weekday=0)
        change = save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="",
            )
        )
        self.assertEqual(LessonChange.objects.get(pk=change.pk).reason, "")


class LessonChangeConflictTests(ValidationFixture):
    def _lesson(self, weekday, slot, room, group=None):
        groups = [group or self.group_a]
        return make_lesson(groups, weekday=weekday, slot=slot, room=room)

    def test_move_into_busy_group_slot_rejected(self):
        self._lesson(weekday=0, slot=1, room=self.room)  # Monday slot 1 (group A)
        moved = self._lesson(weekday=0, slot=2, room=self.room2)  # Monday slot 2
        with self.assertRaises(ValidationError):
            save_lesson_change(
                LessonChange(
                    weekly_lesson=moved,
                    original_date=date(2026, 11, 16),
                    kind=ChangeKind.MOVED,
                    new_date=date(2026, 11, 16),
                    new_slot=1,
                    reason="Перенос",
                )
            )

    def test_move_into_slot_freed_by_cancellation_allowed(self):
        blocked = self._lesson(weekday=0, slot=1, room=self.room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=blocked,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="Отмена",
            )
        )
        moved = self._lesson(weekday=0, slot=2, room=self.room2)
        save_lesson_change(
            LessonChange(
                weekly_lesson=moved,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 16),
                new_slot=1,
                reason="Перенос",
            )
        )

    def test_room_change_into_busy_room_rejected(self):
        self._lesson(weekday=0, slot=1, room=self.room2, group=self.group_b)
        other = self._lesson(weekday=0, slot=1, room=self.room)
        with self.assertRaises(ValidationError):
            save_lesson_change(
                LessonChange(
                    weekly_lesson=other,
                    original_date=date(2026, 11, 16),
                    kind=ChangeKind.ROOM_CHANGED,
                    new_room=self.room2,
                    reason="Замена",
                )
            )

    def test_room_change_into_room_freed_by_move_allowed(self):
        blocker = self._lesson(weekday=0, slot=1, room=self.room2, group=self.group_b)
        save_lesson_change(
            LessonChange(
                weekly_lesson=blocker,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 20),
                new_slot=5,
                reason="Перенос",
            )
        )
        other = self._lesson(weekday=0, slot=1, room=self.room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=other,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.ROOM_CHANGED,
                new_room=self.room2,
                reason="Замена",
            )
        )

    def test_editing_existing_change_no_self_conflict(self):
        lesson = self._lesson(weekday=0, slot=1, room=self.room)
        change = save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.ROOM_CHANGED,
                new_room=self.room2,
                reason="Замена",
            )
        )
        change.reason = "Обновлённая причина"
        save_lesson_change(change)


class LessonChangeDBConstraintTests(ValidationFixture):
    def _lesson(self):
        return make_lesson([self.group_a], weekday=0, slot=1, room=self.room)

    def test_cancelled_with_room_violates_constraint(self):
        lesson = self._lesson()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LessonChange.objects.create(
                    weekly_lesson=lesson,
                    original_date=date(2026, 11, 16),
                    kind=ChangeKind.CANCELLED,
                    new_room=self.room2,
                    reason="x",
                )

    def test_second_change_same_occurrence_violates_constraint(self):
        lesson = self._lesson()
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="x",
            )
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LessonChange.objects.create(
                    weekly_lesson=lesson,
                    original_date=date(2026, 11, 16),
                    kind=ChangeKind.CANCELLED,
                    reason="y",
                )

    # TASK-013: the constraint schedule_change_reason_required is removed (AC13).
    def test_blank_reason_saved_in_db(self):
        lesson = self._lesson()
        with transaction.atomic():
            change = LessonChange.objects.create(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="",
            )
        self.assertEqual(change.reason, "")
