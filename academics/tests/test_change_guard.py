from datetime import date
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from academics.services import attendance_change_guard, student_term_report
from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_student
from core.testing import FrozenClockMixin, moscow
from schedule import guards
from schedule.models import ChangeKind, LessonChange
from schedule.mutations import delete_lesson_change, save_lesson_change
from schedule.tests.helpers import make_discipline, make_lesson, make_room, make_teacher

from .helpers import make_attendance, make_item, make_term


class AttendanceChangeGuardTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FA")
        cls.group = make_group(cls.faculty, "G1")
        cls.student = make_student("sa", cls.group, "REC-A")
        cls.profile = cls.student.student_profile
        cls.room = make_room("room-101")
        cls.room2 = make_room("room-102")
        cls.discipline = make_discipline("Дисциплина")
        cls.lesson = make_lesson(
            [cls.group], weekday=0, slot=2, room=cls.room, discipline=cls.discipline
        )
        cls.term = make_term()
        cls.item = make_item(cls.group, cls.discipline, cls.term)

    def _change(self, kind, original_date, **kwargs):
        return LessonChange(
            weekly_lesson=self.lesson,
            original_date=original_date,
            kind=kind,
            reason="Причина",
            **kwargs,
        )

    def test_cancel_with_attendance_rejected(self):
        make_attendance(self.profile, self.lesson, date(2026, 11, 16), "present")
        change = self._change(ChangeKind.CANCELLED, date(2026, 11, 16))
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(change)
        self.assertIn("отметки посещения", " ".join(cm.exception.messages))
        self.assertFalse(LessonChange.objects.filter(weekly_lesson=self.lesson).exists())

    def test_cancel_without_attendance_allowed(self):
        change = self._change(ChangeKind.CANCELLED, date(2026, 11, 9))
        saved = save_lesson_change(change)
        self.assertIsNotNone(saved.pk)

    def test_edit_existing_change_to_cancel_rejected(self):
        make_attendance(self.profile, self.lesson, date(2026, 11, 16), "present")
        saved = save_lesson_change(
            self._change(ChangeKind.ROOM_CHANGED, date(2026, 11, 16), new_room=self.room2)
        )
        saved.kind = ChangeKind.CANCELLED
        saved.new_room = None
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(saved)
        self.assertIn("отметки посещения", " ".join(cm.exception.messages))

    def test_move_to_future_with_attendance_rejected(self):
        make_attendance(self.profile, self.lesson, date(2026, 11, 16), "present")
        change = self._change(
            ChangeKind.MOVED, date(2026, 11, 16), new_date=date(2026, 11, 20), new_slot=3
        )
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(change)
        self.assertIn("отметки посещения", " ".join(cm.exception.messages))

    def test_move_to_past_with_attendance_allowed_and_visible(self):
        make_attendance(self.profile, self.lesson, date(2026, 11, 16), "present")
        save_lesson_change(
            self._change(
                ChangeKind.MOVED, date(2026, 11, 16), new_date=date(2026, 11, 17), new_slot=3
            )
        )
        report = student_term_report(self.profile, self.term, date(2026, 11, 18))
        disc = next(d for d in report.disciplines if d.item.id == self.item.id)
        self.assertEqual(disc.attendance.present, 1)

    def test_room_and_teacher_change_with_attendance_allowed(self):
        make_attendance(self.profile, self.lesson, date(2026, 11, 16), "present")
        room_change = save_lesson_change(
            self._change(ChangeKind.ROOM_CHANGED, date(2026, 11, 16), new_room=self.room2)
        )
        self.assertIsNotNone(room_change.pk)
        make_attendance(self.profile, self.lesson, date(2026, 11, 9), "present")
        teacher_change = save_lesson_change(
            self._change(
                ChangeKind.TEACHER_REPLACED, date(2026, 11, 9), new_teacher=make_teacher("Замена")
            )
        )
        self.assertIsNotNone(teacher_change.pk)

    def test_edit_reason_of_allowed_move_with_attendance(self):
        make_attendance(self.profile, self.lesson, date(2026, 11, 16), "present")
        move = save_lesson_change(
            self._change(
                ChangeKind.MOVED, date(2026, 11, 16), new_date=date(2026, 11, 17), new_slot=3
            )
        )
        move.reason = "Новая причина"
        save_lesson_change(move)
        self.assertEqual(LessonChange.objects.get(pk=move.pk).reason, "Новая причина")

    def test_delete_move_returning_to_future_rejected(self):
        l2 = make_lesson(
            [self.group], weekday=0, slot=3, room=self.room2, discipline=self.discipline
        )
        move = save_lesson_change(
            LessonChange(
                weekly_lesson=l2,
                original_date=date(2026, 11, 23),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 17),
                new_slot=4,
                reason="Перенос",
            )
        )
        make_attendance(self.profile, l2, date(2026, 11, 23), "present")
        with self.assertRaises(ValidationError) as cm:
            delete_lesson_change(move)
        self.assertIn("отметки посещения", " ".join(cm.exception.messages))

    def test_delete_move_returning_to_past_allowed(self):
        make_attendance(self.profile, self.lesson, date(2026, 11, 16), "present")
        move = save_lesson_change(
            self._change(
                ChangeKind.MOVED, date(2026, 11, 16), new_date=date(2026, 11, 17), new_slot=3
            )
        )
        delete_lesson_change(move)
        self.assertFalse(LessonChange.objects.filter(weekly_lesson=self.lesson).exists())

    def test_admin_cancel_with_attendance_shows_form_error(self):
        make_attendance(self.profile, self.lesson, date(2026, 11, 16), "present")
        superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")
        self.client.force_login(superuser)
        response = self.client.post(
            reverse("admin:schedule_lessonchange_add"),
            {
                "weekly_lesson": self.lesson.pk,
                "original_date": "2026-11-16",
                "kind": "cancelled",
                "reason": "Отмена",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "отметки посещения")
        self.assertFalse(
            LessonChange.objects.filter(
                weekly_lesson=self.lesson, original_date=date(2026, 11, 16)
            ).exists()
        )

    def test_clock_boundary_move(self):
        make_attendance(self.profile, self.lesson, date(2026, 11, 16), "present")
        with mock.patch("django.utils.timezone.now", return_value=moscow("2026-11-17 23:59:59")):
            change = self._change(
                ChangeKind.MOVED, date(2026, 11, 16), new_date=date(2026, 11, 18), new_slot=3
            )
            with self.assertRaises(ValidationError):
                save_lesson_change(change)
        with mock.patch("django.utils.timezone.now", return_value=moscow("2026-11-18 00:00:00")):
            change = self._change(
                ChangeKind.MOVED, date(2026, 11, 16), new_date=date(2026, 11, 18), new_slot=3
            )
            save_lesson_change(change)

    def test_edit_move_original_date_returns_records_to_future_rejected(self):
        l2 = make_lesson(
            [self.group], weekday=0, slot=3, room=self.room2, discipline=self.discipline
        )
        move = save_lesson_change(
            LessonChange(
                weekly_lesson=l2,
                original_date=date(2026, 11, 23),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 17),
                new_slot=4,
                reason="Перенос",
            )
        )
        make_attendance(self.profile, l2, date(2026, 11, 23), "present")
        row = LessonChange.objects.get(pk=move.pk)
        row.original_date = date(2026, 11, 30)
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(row)
        self.assertIn("отметки посещения", " ".join(cm.exception.messages))

    def test_edit_move_to_room_change_returns_records_to_future_rejected(self):
        l2 = make_lesson(
            [self.group], weekday=0, slot=3, room=self.room2, discipline=self.discipline
        )
        move = save_lesson_change(
            LessonChange(
                weekly_lesson=l2,
                original_date=date(2026, 11, 23),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 17),
                new_slot=4,
                reason="Перенос",
            )
        )
        make_attendance(self.profile, l2, date(2026, 11, 23), "present")
        row = LessonChange.objects.get(pk=move.pk)
        row.kind = ChangeKind.ROOM_CHANGED
        row.new_date = None
        row.new_slot = None
        row.new_room = self.room
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(row)
        self.assertIn("отметки посещения", " ".join(cm.exception.messages))

    def test_edit_without_releasing_records_allowed(self):
        make_attendance(self.profile, self.lesson, date(2026, 11, 16), "present")
        move = save_lesson_change(
            self._change(
                ChangeKind.MOVED, date(2026, 11, 16), new_date=date(2026, 11, 17), new_slot=3
            )
        )
        row = LessonChange.objects.get(pk=move.pk)
        row.reason = "Новая причина"
        save_lesson_change(row)
        self.assertEqual(LessonChange.objects.get(pk=move.pk).reason, "Новая причина")


class GuardRegistryTests(SimpleTestCase):
    def test_academics_guard_registered(self):
        self.assertIn(attendance_change_guard, guards._guards)

    def test_register_is_idempotent(self):
        def guard(change, deleting):  # noqa: ANN001, ARG001
            return []

        guards.register_change_guard(guard)
        try:
            guards.register_change_guard(guard)
            self.assertEqual(guards._guards.count(guard), 1)
        finally:
            guards._guards.remove(guard)
