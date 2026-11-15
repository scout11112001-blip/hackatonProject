"""Service tests for the chat app."""

import uuid
from datetime import timedelta
from unittest import mock

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import QuerySet
from django.test import TestCase

from accounts.tests.helpers import make_staff
from chat.constants import FRAGMENT_LIMIT, HISTORY_LIMIT, RATE_LIMIT_MESSAGES
from chat.models import AuthorRole, Dialog, Message
from chat.services import (
    load_history,
    mark_read,
    messages_after,
    normalize_text,
    send_staff_message,
    send_student_message,
    text_errors,
)
from chat.tests.helpers import add_message, make_dialog
from core.testing import FrozenClockMixin, moscow
from notifications.tests.helpers import make_world

NOW = "2026-11-11 12:00"


class ServiceTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.fx = cls.w.fx
        cls.ax = cls.w.ax
        cls.sx = cls.w.sx
        cls.sy = cls.w.sy
        cls.ax_profile = cls.w.ax_profile

    def test_first_message_creates_dialog(self):
        self.assertFalse(Dialog.objects.filter(student=self.ax_profile).exists())
        message = send_student_message(self.ax_profile, "Привет", None)
        self.assertEqual(message.dialog.student, self.ax_profile)

    def test_second_message_same_dialog(self):
        first = send_student_message(self.ax_profile, "Привет", None)
        second = send_student_message(self.ax_profile, "Ещё", None)
        self.assertEqual(first.dialog.pk, second.dialog.pk)
        self.assertEqual(Dialog.objects.filter(student=self.ax_profile).count(), 1)

    def test_text_normalised_and_limited(self):
        self.assertEqual(normalize_text("a\r\nb  "), "a\nb")
        self.assertEqual(text_errors("a" * 2000), [])
        self.assertNotEqual(text_errors("a" * 2001), [])
        self.assertEqual(text_errors(normalize_text("a" * 2000 + "\r\n")), [])

    def test_empty_rejected(self):
        for text in ("", "  \n "):
            with self.assertRaises(ValidationError):
                send_student_message(self.ax_profile, text, None)
        self.assertFalse(Dialog.objects.filter(student=self.ax_profile).exists())

    def test_rate_limit(self):
        for _ in range(RATE_LIMIT_MESSAGES):
            send_student_message(self.ax_profile, "сообщение", uuid.uuid4())
        with self.assertRaises(ValidationError):
            send_student_message(self.ax_profile, "лишнее", uuid.uuid4())
        self.assertEqual(Message.objects.count(), RATE_LIMIT_MESSAGES)

    def test_rate_limit_window_moves(self):
        dialog = make_dialog(self.ax_profile)
        old = moscow(NOW) - timedelta(minutes=11)
        for _ in range(RATE_LIMIT_MESSAGES):
            add_message(dialog, self.ax, AuthorRole.STUDENT, created_at=old)
        message = send_student_message(self.ax_profile, "новая", None)
        self.assertEqual(message.dialog.pk, dialog.pk)

    def test_staff_no_rate_limit(self):
        dialog = make_dialog(self.ax_profile)
        for _ in range(25):
            send_staff_message(dialog, self.sx, "ответ", uuid.uuid4())
        self.assertEqual(Message.objects.filter(dialog=dialog).count(), 25)

    def test_same_client_token_returns_existing(self):
        token = uuid.uuid4()
        first = send_student_message(self.ax_profile, "Привет", token)
        second = send_student_message(self.ax_profile, "Привет", token)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Message.objects.filter(dialog=first.dialog).count(), 1)
        # A repeated token does not count towards the rate limit.
        for _ in range(RATE_LIMIT_MESSAGES - 1):
            send_student_message(self.ax_profile, "заполнение", uuid.uuid4())
        self.assertEqual(send_student_message(self.ax_profile, "Привет", token).pk, first.pk)

    def test_two_staff_replies_both_kept_in_id_order(self):
        sx2 = make_staff("sx2", self.fx)
        dialog = make_dialog(self.ax_profile)
        first = send_staff_message(dialog, self.sx, "первый", None)
        second = send_staff_message(dialog, sx2, "второй", None)
        self.assertLess(first.pk, second.pk)
        self.assertEqual(Message.objects.filter(dialog=dialog).count(), 2)
        dialog.refresh_from_db()
        self.assertEqual(dialog.last_message_id, second.pk)

    def test_send_locks_dialog(self):
        orig = QuerySet.select_for_update
        with mock.patch.object(
            QuerySet, "select_for_update", autospec=True, side_effect=orig
        ) as spy:
            send_student_message(self.ax_profile, "студент", None)
            dialog = Dialog.objects.get(student=self.ax_profile)
            send_staff_message(dialog, self.sx, "ответ", None)
        self.assertEqual(spy.call_count, 2)

    def test_staff_cannot_write_other_faculty(self):
        dialog = make_dialog(self.ax_profile)
        with self.assertRaises(PermissionDenied):
            send_staff_message(dialog, self.sy, "чужая", None)
        self.assertEqual(Message.objects.filter(dialog=dialog).count(), 0)

    def test_student_cannot_use_staff_send(self):
        dialog = make_dialog(self.ax_profile)
        with self.assertRaises(PermissionDenied):
            send_staff_message(dialog, self.ax, "нельзя", None)

    def test_created_at_is_frozen_clock(self):
        message = send_student_message(self.ax_profile, "Привет", None)
        self.assertEqual(message.created_at, moscow(NOW))

    def test_mark_read_monotonic(self):
        dialog = make_dialog(self.ax_profile)
        mark_read(dialog.pk, "student", 5)
        dialog.refresh_from_db()
        self.assertEqual(dialog.student_read_id, 5)
        mark_read(dialog.pk, "student", 3)
        dialog.refresh_from_db()
        self.assertEqual(dialog.student_read_id, 5)
        mark_read(dialog.pk, "student", 0)
        dialog.refresh_from_db()
        self.assertEqual(dialog.student_read_id, 5)

    def test_history_limit(self):
        dialog = make_dialog(self.ax_profile)
        for _ in range(105):
            add_message(dialog, self.ax, AuthorRole.STUDENT)
        messages, truncated = load_history(dialog)
        self.assertTrue(truncated)
        self.assertEqual(len(messages), HISTORY_LIMIT)
        ids = [m.pk for m in messages]
        self.assertEqual(ids, sorted(ids))
        expected = sorted(
            Message.objects.order_by("-id").values_list("id", flat=True)[:HISTORY_LIMIT]
        )
        self.assertEqual(ids, expected)

    def test_messages_after(self):
        dialog = make_dialog(self.ax_profile)
        rows = [add_message(dialog, self.ax, AuthorRole.STUDENT) for _ in range(60)]
        after = rows[4].pk
        result = messages_after(dialog, after)
        self.assertEqual(len(result), FRAGMENT_LIMIT)
        self.assertEqual([m.pk for m in result], [m.pk for m in rows[5:55]])
