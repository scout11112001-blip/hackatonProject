"""Selector tests for the chat app."""

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from chat.models import AuthorRole
from chat.selectors import dialogs_visible_to, staff_dialog_list, student_unread_count
from chat.tests.helpers import add_message, make_dialog
from core.testing import FrozenClockMixin
from notifications.tests.helpers import make_world

NOW = "2026-11-11 12:00"


class SelectorTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.ax_dialog = make_dialog(cls.w.ax_profile)
        cls.bx_dialog = make_dialog(cls.w.bx_profile)
        cls.ay_dialog = make_dialog(cls.w.ay_profile)

    def test_staff_sees_own_faculty_only(self):
        visible = set(dialogs_visible_to(self.w.sx))
        self.assertEqual(visible, {self.ax_dialog, self.bx_dialog})
        visible_y = set(dialogs_visible_to(self.w.sy))
        self.assertEqual(visible_y, {self.ay_dialog})

    def test_student_sees_own_only(self):
        self.assertEqual(set(dialogs_visible_to(self.w.ax)), {self.ax_dialog})
        self.assertEqual(set(dialogs_visible_to(self.w.bx)), {self.bx_dialog})

    def test_superuser_and_anonymous_none(self):
        self.assertFalse(list(dialogs_visible_to(self.w.root)))
        self.assertFalse(list(dialogs_visible_to(AnonymousUser())))

    def test_inactive_student_dialog_hidden_from_staff(self):
        self.w.bx.is_active = False
        self.w.bx.save(update_fields=["is_active"])
        self.assertEqual(set(dialogs_visible_to(self.w.sx)), {self.ax_dialog})

    def test_unread_first_then_newest(self):
        # ax_dialog has an unread student message; bx_dialog has a staff message (no unread).
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(self.bx_dialog, self.w.sx, AuthorRole.STAFF)
        listed = list(staff_dialog_list(self.w.sx))
        self.assertEqual(listed[0].pk, self.ax_dialog.pk)
        self.assertEqual(listed[1].pk, self.bx_dialog.pk)

    def test_unread_counts(self):
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(self.ax_dialog, self.w.sx, AuthorRole.STAFF)
        by_pk = {d.pk: d for d in staff_dialog_list(self.w.sx)}
        self.assertEqual(by_pk[self.ax_dialog.pk].unread, 2)
        self.assertEqual(by_pk[self.bx_dialog.pk].unread, 0)

    def test_one_query(self):
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        with self.assertNumQueries(1):
            list(staff_dialog_list(self.w.sx))

    def test_counts_only_staff_after_marker(self):
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        reply = add_message(self.ax_dialog, self.w.sx, AuthorRole.STAFF)
        self.assertEqual(student_unread_count(self.w.ax), 1)
        self.ax_dialog.student_read_id = reply.pk
        self.ax_dialog.save(update_fields=["student_read_id"])
        self.assertEqual(student_unread_count(self.w.ax), 0)
        add_message(self.ax_dialog, self.w.sx, AuthorRole.STAFF)
        self.assertEqual(student_unread_count(self.w.ax), 1)

    def test_zero_without_dialog(self):
        self.assertEqual(student_unread_count(self.w.cx), 0)

    def test_staff_and_anonymous_no_query(self):
        with self.assertNumQueries(0):
            self.assertEqual(student_unread_count(self.w.sx), 0)
        with self.assertNumQueries(0):
            self.assertEqual(student_unread_count(AnonymousUser()), 0)
