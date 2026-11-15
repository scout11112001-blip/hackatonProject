"""Feed integration tests for chat replies."""

from django.test import TestCase

from accounts.models import User
from chat.models import AuthorRole
from chat.selectors import student_unread_count
from chat.services import mark_read
from chat.tests.helpers import add_message, make_dialog
from core.testing import FrozenClockMixin, moscow
from notifications.feed import badge_for_user, build_feed, student_context, unread_count
from notifications.services import mark_seen
from notifications.tests.helpers import make_world

NOW = "2026-11-11 12:00"


def _ctx(user):
    return student_context(user)


class ChatFeedTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_unread_staff_reply_in_feed(self):
        dialog = make_dialog(self.w.ax_profile)
        reply = add_message(dialog, self.w.sx, AuthorRole.STAFF, text="a" * 300)
        chat = next(i for i in build_feed(_ctx(self.w.ax)) if i.kind == "chat_reply")
        self.assertEqual(chat.title, "Новое сообщение от деканата")
        self.assertLessEqual(len(chat.body), 200)
        self.assertTrue(chat.body.endswith("…"))
        self.assertEqual(chat.url, "/chat/")
        self.assertEqual(chat.key, f"chat-{reply.pk}")

    def test_own_student_messages_not_in_feed(self):
        dialog = make_dialog(self.w.ax_profile)
        add_message(dialog, self.w.ax, AuthorRole.STUDENT, text="моё сообщение")
        self.assertFalse(any(i.kind == "chat_reply" for i in build_feed(_ctx(self.w.ax))))

    def test_read_reply_leaves_feed(self):
        dialog = make_dialog(self.w.ax_profile)
        reply = add_message(dialog, self.w.sx, AuthorRole.STAFF)
        self.assertTrue(any(i.kind == "chat_reply" for i in build_feed(_ctx(self.w.ax))))
        mark_read(dialog.pk, "student", reply.pk)
        self.assertFalse(any(i.kind == "chat_reply" for i in build_feed(_ctx(self.w.ax))))

    def test_reply_counts_in_badge_once(self):
        dialog = make_dialog(self.w.ax_profile)
        add_message(dialog, self.w.sx, AuthorRole.STAFF)
        self.assertEqual(unread_count(_ctx(self.w.ax)), 1)
        self.assertEqual(student_unread_count(self.w.ax), 1)
        mark_seen(self.w.ax.pk, moscow(NOW))
        self.assertEqual(unread_count(_ctx(self.w.ax)), 0)
        self.assertEqual(student_unread_count(self.w.ax), 1)

    def test_other_student_reply_not_in_feed(self):
        other = make_dialog(self.w.bx_profile)
        add_message(other, self.w.sx, AuthorRole.STAFF)
        self.assertFalse(any(i.kind == "chat_reply" for i in build_feed(_ctx(self.w.ax))))

    def test_badge_still_three_queries(self):
        dialog = make_dialog(self.w.ax_profile)
        add_message(dialog, self.w.sx, AuthorRole.STAFF)
        user = User.objects.get(pk=self.w.ax.pk)
        with self.assertNumQueries(3):
            badge_for_user(user)
