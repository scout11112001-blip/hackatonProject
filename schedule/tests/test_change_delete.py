from datetime import date
from unittest import mock

from django.contrib.admin.models import DELETION, LogEntry
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from core.testing import FrozenClockMixin
from schedule.locking import lock_rooms_and_groups
from schedule.models import ChangeKind, LessonChange
from schedule.mutations import delete_lesson_change, save_lesson_change
from schedule.tests.helpers import make_lesson, make_room, make_teacher


class DeleteLessonChangeTests(FrozenClockMixin, TestCase):
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

    def _change(self, lesson, kind, original_date, **kwargs):
        return LessonChange(
            weekly_lesson=lesson,
            original_date=original_date,
            kind=kind,
            reason="Причина",
            **kwargs,
        )

    def test_reviewer_scenario_room_conflict_rejected(self):
        cancel = save_lesson_change(
            self._change(self.l_a, ChangeKind.CANCELLED, date(2026, 11, 23))
        )
        l_b = make_lesson([self.g2], weekday=1, slot=1, room=self.r2)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l_b,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 23),
                new_slot=2,
                new_room=self.r1,
                reason="Перенос",
            )
        )
        with self.assertRaises(ValidationError) as cm:
            delete_lesson_change(cancel)
        msg = " ".join(cm.exception.messages)
        self.assertIn(f"аудитория {self.r1.number}", msg)
        self.assertIn("23.11.2026", msg)
        self.assertTrue(LessonChange.objects.filter(pk=cancel.pk).exists())

    def test_group_conflict_rejected(self):
        cancel = save_lesson_change(
            self._change(self.l_a, ChangeKind.CANCELLED, date(2026, 11, 23))
        )
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
        with self.assertRaises(ValidationError) as cm:
            delete_lesson_change(cancel)
        self.assertIn("группа G1", " ".join(cm.exception.messages))

    def test_room_changed_restore_conflict_rejected(self):
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
        with self.assertRaises(ValidationError) as cm:
            delete_lesson_change(room_change)
        self.assertIn(f"аудитория {self.r1.number}", " ".join(cm.exception.messages))

    def test_moved_restore_conflict_rejected(self):
        move = save_lesson_change(
            self._change(
                self.l_a,
                ChangeKind.MOVED,
                date(2026, 11, 23),
                new_date=date(2026, 11, 25),
                new_slot=4,
            )
        )
        l_e = make_lesson([self.g2], weekday=1, slot=1, room=self.r4)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l_e,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 23),
                new_slot=2,
                new_room=self.r1,
                reason="Перенос",
            )
        )
        with self.assertRaises(ValidationError) as cm:
            delete_lesson_change(move)
        self.assertIn("аудитория", " ".join(cm.exception.messages))

    def test_delete_without_conflict_allowed(self):
        cancel = save_lesson_change(
            self._change(self.l_a, ChangeKind.CANCELLED, date(2026, 11, 23))
        )
        delete_lesson_change(cancel)
        self.assertFalse(LessonChange.objects.filter(pk=cancel.pk).exists())

    def test_delete_teacher_replacement_always_allowed(self):
        # TEACHER_REPLACED cannot create a room/group conflict on restore, so it is
        # deleted unconditionally (restored_occurrence_conflicts returns [] for this kind).
        tr = save_lesson_change(
            self._change(
                self.l_a,
                ChangeKind.TEACHER_REPLACED,
                date(2026, 11, 23),
                new_teacher=make_teacher("Замена"),
            )
        )
        delete_lesson_change(tr)
        self.assertFalse(LessonChange.objects.filter(pk=tr.pk).exists())

    def test_delete_moved_in_target_never_conflicts(self):
        cancel = save_lesson_change(
            self._change(self.l_a, ChangeKind.CANCELLED, date(2026, 11, 23))
        )
        l_b = make_lesson([self.g2], weekday=1, slot=1, room=self.r2)
        move_b = save_lesson_change(
            LessonChange(
                weekly_lesson=l_b,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 23),
                new_slot=2,
                new_room=self.r1,
                reason="Перенос",
            )
        )
        delete_lesson_change(move_b)
        self.assertTrue(LessonChange.objects.filter(pk=cancel.pk).exists())

    def test_delete_locks_room_and_groups(self):
        cancel = save_lesson_change(
            self._change(self.l_a, ChangeKind.CANCELLED, date(2026, 11, 23))
        )
        with mock.patch("schedule.locking.lock_rooms_and_groups", wraps=lock_rooms_and_groups) as m:
            delete_lesson_change(cancel)
        m.assert_called_once()
        args, _ = m.call_args
        self.assertEqual(args[0], [self.l_a.room_id])
        self.assertEqual(set(args[1]), {self.g1.pk})

    def test_delete_is_atomic_on_error(self):
        cancel = save_lesson_change(
            self._change(self.l_a, ChangeKind.CANCELLED, date(2026, 11, 23))
        )
        l_b = make_lesson([self.g2], weekday=1, slot=1, room=self.r2)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l_b,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 23),
                new_slot=2,
                new_room=self.r1,
                reason="Перенос",
            )
        )
        before = LessonChange.objects.count()
        with self.assertRaises(ValidationError):
            delete_lesson_change(cancel)
        self.assertEqual(LessonChange.objects.count(), before)


class DeleteLessonChangeAdminTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.g1 = make_group(cls.faculty, "G1")
        cls.g2 = make_group(cls.faculty, "G2")
        cls.r1 = make_room("room-101")
        cls.r2 = make_room("room-102")
        cls.l_a = make_lesson([cls.g1], weekday=0, slot=2, room=cls.r1)
        cls.superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")
        cls.student = make_student("stu", cls.g1, "REC-1")
        cls.staff = make_staff("stf", cls.faculty)

    def _cancel(self):
        return save_lesson_change(
            LessonChange(
                weekly_lesson=self.l_a,
                original_date=date(2026, 11, 23),
                kind=ChangeKind.CANCELLED,
                reason="Отмена",
            )
        )

    def test_admin_invalid_delete_shows_error(self):
        cancel = self._cancel()
        l_b = make_lesson([self.g2], weekday=1, slot=1, room=self.r2)
        save_lesson_change(
            LessonChange(
                weekly_lesson=l_b,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 23),
                new_slot=2,
                new_room=self.r1,
                reason="Перенос",
            )
        )
        self.client.force_login(self.superuser)
        url = reverse("admin:schedule_lessonchange_delete", args=[cancel.pk])
        response = self.client.post(url, {"post": "yes"}, follow=True)
        self.assertContains(response, "Нельзя удалить изменение")
        self.assertTrue(LessonChange.objects.filter(pk=cancel.pk).exists())
        self.assertEqual(LogEntry.objects.filter(action_flag=DELETION).count(), 0)

    def test_admin_valid_delete(self):
        cancel = self._cancel()
        self.client.force_login(self.superuser)
        url = reverse("admin:schedule_lessonchange_delete", args=[cancel.pk])
        response = self.client.post(url, {"post": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(LessonChange.objects.filter(pk=cancel.pk).exists())

    def test_admin_bulk_delete_action_removed(self):
        cancel = self._cancel()
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("admin:schedule_lessonchange_changelist"))
        action_form = response.context["action_form"]
        if action_form is not None:
            choices = [c[0] for c in action_form.fields["action"].choices]
            self.assertNotIn("delete_selected", choices)
        response = self.client.post(
            reverse("admin:schedule_lessonchange_changelist"),
            {"action": "delete_selected", "_selected_action": [cancel.pk]},
        )
        self.assertTrue(LessonChange.objects.filter(pk=cancel.pk).exists())

    def test_non_superuser_cannot_delete_change(self):
        cancel = self._cancel()
        url = reverse("admin:schedule_lessonchange_delete", args=[cancel.pk])
        for user in (self.student, self.staff):
            self.client.force_login(user)
            response = self.client.post(url, {"post": "yes"})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(LessonChange.objects.filter(pk=cancel.pk).exists())
