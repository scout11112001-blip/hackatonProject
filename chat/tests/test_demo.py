"""Seed tests for the chat demo data."""

import os
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from chat.models import AuthorRole, Dialog, Message
from chat.selectors import staff_dialog_list, student_unread_count
from core.testing import FrozenClockMixin
from notifications.feed import build_feed, student_context

PASSWORD = "Local-Demo-Pass-2026!"


class ChatSeedTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-22 12:00"

    def _seed(self):
        out = StringIO()
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": PASSWORD}):
            call_command("seed_demo", stdout=out)
        return out.getvalue()

    def test_dialogs_and_messages(self):
        self._seed()
        self.assertEqual(Dialog.objects.count(), 3)
        self.assertEqual(Message.objects.count(), 8)
        for username in ("student1", "student2"):
            student = User.objects.get(username=username)
            roles = set(
                Message.objects.filter(dialog__student__user=student).values_list(
                    "author_role", flat=True
                )
            )
            self.assertEqual(roles, {AuthorRole.STUDENT, AuthorRole.STAFF})

    def test_idempotent(self):
        self._seed()
        output = self._seed()
        self.assertEqual(Dialog.objects.count(), 3)
        self.assertEqual(Message.objects.count(), 8)
        self.assertIn("Chat ready: 0 dialogs, 0 messages.", output)

    def test_student1_has_unread_reply(self):
        self._seed()
        student1 = User.objects.get(username="student1")
        self.assertEqual(student_unread_count(student1), 1)
        items = build_feed(student_context(student1))
        self.assertTrue(any(i.kind == "chat_reply" for i in items))

    def test_each_faculty_has_unread_student_message(self):
        self._seed()
        staff1 = User.objects.get(username="staff1")
        staff2 = User.objects.get(username="staff2")
        for staff in (staff1, staff2):
            self.assertTrue(any(d.unread >= 1 for d in staff_dialog_list(staff)))

    def test_messages_in_past_and_ordered(self):
        self._seed()
        now = timezone.now()
        for dialog in Dialog.objects.all():
            rows = list(dialog.messages.order_by("id"))
            for message in rows:
                self.assertLessEqual(message.created_at, now)
            times = [m.created_at for m in rows]
            self.assertEqual(times, sorted(times))
