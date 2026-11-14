from datetime import date
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group
from core.testing import FrozenClockMixin
from schedule.locking import lock_rooms_and_groups
from schedule.models import ChangeKind, LessonChange
from schedule.mutations import save_lesson_change
from schedule.tests.helpers import make_lesson, make_room, make_teacher


class EditLessonChangeTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.g1 = make_group(cls.faculty, "G1")
        cls.g2 = make_group(cls.faculty, "G2")
        cls.g3 = make_group(cls.faculty, "G3")
        cls.r1 = make_room("room-101")
        cls.r2 = make_room("room-102")
        cls.r3 = make_room("room-103")
        cls.r4 = make_room("room-104")
        cls.r5 = make_room("room-105")
        cls.r6 = make_room("room-106")
        cls.l_a = make_lesson([cls.g1], weekday=0, slot=2, room=cls.r1)
        cls.l_b = make_lesson([cls.g2], weekday=1, slot=1, room=cls.r2)

    def _change(self, lesson, kind, original_date, **kwargs):
        return LessonChange(
            weekly_lesson=lesson,
            original_date=original_date,
            kind=kind,
            reason="Причина",
            **kwargs,
        )

    def _cancel(self, original_date=date(2026, 11, 23)):
        return save_lesson_change(self._change(self.l_a, ChangeKind.CANCELLED, original_date))

    def _move_b_into_r1(self):
        return save_lesson_change(
            LessonChange(
                weekly_lesson=self.l_b,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 23),
                new_slot=2,
                new_room=self.r1,
                reason="Перенос",
            )
        )

    def _reload(self, change):
        return LessonChange.objects.get(pk=change.pk)

    def test_cancel_to_teacher_replaced_rejected(self):
        cancel = self._cancel()
        self._move_b_into_r1()
        row = self._reload(cancel)
        row.kind = ChangeKind.TEACHER_REPLACED
        row.new_teacher = make_teacher("Замена")
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(row)
        msg = " ".join(cm.exception.messages)
        self.assertIn(f"аудитория {self.r1.number}", msg)
        self.assertIn("23.11.2026", msg)
        self.assertEqual(self._reload(cancel).kind, ChangeKind.CANCELLED)

    def test_cancel_original_date_change_rejected(self):
        cancel = self._cancel()
        self._move_b_into_r1()
        row = self._reload(cancel)
        row.original_date = date(2026, 11, 30)
        with self.assertRaises(ValidationError):
            save_lesson_change(row)
        self.assertEqual(self._reload(cancel).original_date, date(2026, 11, 23))

    def test_room_changed_to_teacher_replaced_rejected(self):
        room_change = save_lesson_change(
            self._change(self.l_a, ChangeKind.ROOM_CHANGED, date(2026, 11, 23), new_room=self.r5)
        )
        l_d = make_lesson([self.g3], weekday=0, slot=2, room=self.r6)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l_d,
                original_date=date(2026, 11, 23),
                kind=ChangeKind.ROOM_CHANGED,
                new_room=self.r1,
                reason="Замена",
            )
        )
        row = self._reload(room_change)
        row.kind = ChangeKind.TEACHER_REPLACED
        row.new_room = None
        row.new_teacher = make_teacher("Замена")
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(row)
        self.assertIn(f"аудитория {self.r1.number}", " ".join(cm.exception.messages))

    def test_group_conflict_on_restore_rejected(self):
        cancel = self._cancel()
        l_c = make_lesson([self.g1], weekday=1, slot=1, room=self.r3)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l_c,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 23),
                new_slot=2,
                reason="Перенос",
            )
        )
        row = self._reload(cancel)
        row.original_date = date(2026, 11, 30)
        with self.assertRaises(ValidationError) as cm:
            save_lesson_change(row)
        self.assertIn("группа G1", " ".join(cm.exception.messages))

    def test_allowed_edits(self):
        # 1. reason change
        cancel = self._cancel()
        self._move_b_into_r1()
        row = self._reload(cancel)
        row.reason = "Новая причина"
        save_lesson_change(row)
        self.assertEqual(self._reload(cancel).reason, "Новая причина")
        LessonChange.objects.all().delete()

        # 2. original_date change when nothing occupies the old slot
        cancel2 = self._cancel()
        move_b = self._move_b_into_r1()
        LessonChange.objects.get(pk=move_b.pk).delete()
        row = self._reload(cancel2)
        row.original_date = date(2026, 11, 30)
        save_lesson_change(row)
        self.assertEqual(self._reload(cancel2).original_date, date(2026, 11, 30))
        LessonChange.objects.all().delete()

        # 3. CANCELLED -> MOVED with the old slot still occupied by B (no false positive)
        cancel3 = self._cancel()
        self._move_b_into_r1()
        row = self._reload(cancel3)
        row.kind = ChangeKind.MOVED
        row.new_date = date(2026, 11, 25)
        row.new_slot = 4
        save_lesson_change(row)
        self.assertEqual(self._reload(cancel3).kind, ChangeKind.MOVED)

    def test_move_target_change_allowed(self):
        move = save_lesson_change(
            self._change(
                self.l_a,
                ChangeKind.MOVED,
                date(2026, 11, 23),
                new_date=date(2026, 11, 25),
                new_slot=4,
            )
        )
        row = self._reload(move)
        row.new_slot = 5
        save_lesson_change(row)
        self.assertEqual(self._reload(move).new_slot, 5)

    def test_move_original_date_change_no_self_conflict(self):
        move = save_lesson_change(
            self._change(
                self.l_a,
                ChangeKind.MOVED,
                date(2026, 11, 23),
                new_date=date(2026, 11, 25),
                new_slot=4,
            )
        )
        row = self._reload(move)
        row.original_date = date(2026, 11, 30)
        save_lesson_change(row)
        self.assertEqual(self._reload(move).original_date, date(2026, 11, 30))

    def test_admin_edit_shows_form_error(self):
        superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")
        cancel = self._cancel()
        self._move_b_into_r1()
        self.client.force_login(superuser)
        url = reverse("admin:schedule_lessonchange_change", args=[cancel.pk])
        response = self.client.post(
            url,
            {
                "weekly_lesson": self.l_a.pk,
                "original_date": "2026-11-23",
                "kind": "teacher_replaced",
                "new_teacher": make_teacher("Замена").pk,
                "reason": "Замена",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Нельзя так изменить запись")
        self.assertEqual(self._reload(cancel).kind, ChangeKind.CANCELLED)

    def test_edit_locks_once_in_order(self):
        cancel = self._cancel()
        self._move_b_into_r1()
        row = self._reload(cancel)
        row.original_date = date(2026, 11, 30)
        with mock.patch("schedule.locking.lock_rooms_and_groups", wraps=lock_rooms_and_groups) as m:
            with self.assertRaises(ValidationError):
                save_lesson_change(row)
        calls = m.call_args_list
        self.assertGreaterEqual(len(calls), 1)
        first_args, _ = calls[0]
        self.assertEqual({r for r in first_args[0] if r is not None}, {self.r1.pk})
        self.assertEqual(set(first_args[1]), {self.g1.pk})
