"""Selector tests for the chat app."""

from django.contrib.auth.models import AnonymousUser
from django.db.models import F
from django.test import TestCase

from accounts.models import User
from accounts.tests.helpers import make_staff, make_student
from chat.models import AuthorRole, Message
from chat.selectors import (
    chat_unread_count,
    dialogs_visible_to,
    staff_dialog_list,
    staff_unread_count,
    student_unread_count,
)
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


class StaffUnreadCountTests(FrozenClockMixin, TestCase):
    """TASK-018: the "Чаты (n)" count, same rule as the "new" count of the staff chat list."""

    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.ax_dialog = make_dialog(cls.w.ax_profile)
        cls.bx_dialog = make_dialog(cls.w.bx_profile)
        cls.ay_dialog = make_dialog(cls.w.ay_profile)

    def test_counts_own_faculty_only(self):
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(self.bx_dialog, self.w.bx, AuthorRole.STUDENT)
        for _ in range(4):
            add_message(self.ay_dialog, self.w.ay, AuthorRole.STUDENT)
        self.assertEqual(staff_unread_count(self.w.sx), 3)
        self.assertEqual(staff_unread_count(self.w.sy), 4)

    def test_staff_messages_not_counted(self):
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(self.ax_dialog, self.w.sx, AuthorRole.STAFF)
        sx2 = make_staff("sx2", self.w.fx)
        add_message(self.bx_dialog, sx2, AuthorRole.STAFF)
        self.assertEqual(staff_unread_count(self.w.sx), 1)
        self.assertEqual(staff_unread_count(sx2), 1)

    def test_same_as_staff_list(self):
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        reply = add_message(self.ax_dialog, self.w.sx, AuthorRole.STAFF)
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(self.bx_dialog, self.w.bx, AuthorRole.STUDENT)
        self.ax_dialog.staff_read_id = reply.pk
        self.ax_dialog.save(update_fields=["staff_read_id"])
        listed = sum(d.unread for d in staff_dialog_list(self.w.sx))
        self.assertEqual(listed, 2)
        self.assertEqual(staff_unread_count(self.w.sx), listed)

    def test_shared_read_marker(self):
        sx2 = make_staff("sx2", self.w.fx)
        first = add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        self.assertEqual(staff_unread_count(self.w.sx), 1)
        self.assertEqual(staff_unread_count(sx2), 1)
        # One staff member reads the dialog: the count drops for every staff member of the faculty.
        self.ax_dialog.staff_read_id = first.pk
        self.ax_dialog.save(update_fields=["staff_read_id"])
        self.assertEqual(staff_unread_count(self.w.sx), 0)
        self.assertEqual(staff_unread_count(sx2), 0)
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        self.assertEqual(staff_unread_count(self.w.sx), 1)

    def test_inactive_student_not_counted(self):
        add_message(self.bx_dialog, self.w.bx, AuthorRole.STUDENT)
        self.w.bx.is_active = False
        self.w.bx.save(update_fields=["is_active"])
        self.assertEqual(staff_unread_count(self.w.sx), 0)

    def test_staff_without_profile_zero(self):
        orphan = User.objects.create_user(username="orphan", role=User.Role.STAFF)
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        self.assertEqual(staff_unread_count(orphan), 0)

    def test_other_roles_zero_without_query(self):
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        for user in (self.w.ax, self.w.root, AnonymousUser()):
            with self.subTest(user=str(user)), self.assertNumQueries(0):
                self.assertEqual(staff_unread_count(user), 0)

    def test_matches_visibility_rule(self):
        sx2 = make_staff("sx2", self.w.fx)
        orphan = User.objects.create_user(username="orphan", role=User.Role.STAFF)
        cx_dialog = make_dialog(self.w.cx_profile)
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(self.bx_dialog, self.w.bx, AuthorRole.STUDENT)
        add_message(cx_dialog, self.w.cx, AuthorRole.STUDENT)
        add_message(cx_dialog, self.w.sx, AuthorRole.STAFF)
        add_message(self.ay_dialog, self.w.ay, AuthorRole.STUDENT)
        self.w.bx.is_active = False
        self.w.bx.save(update_fields=["is_active"])
        for user in (self.w.sx, sx2, self.w.sy, orphan):
            expected = Message.objects.filter(
                dialog__in=dialogs_visible_to(user),
                author_role=AuthorRole.STUDENT,
                id__gt=F("dialog__staff_read_id"),
            ).count()
            with self.subTest(user=user.username):
                self.assertEqual(staff_unread_count(user), expected)
        self.assertEqual(staff_unread_count(self.w.sx), 2)

    def test_one_query(self):
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        user = User.objects.get(pk=self.w.sx.pk)
        with self.assertNumQueries(1):
            self.assertEqual(staff_unread_count(user), 1)
        for i in range(5):
            student = make_student(f"extra{i}", self.w.gx1, f"ST-EX-{i}")
            dialog = make_dialog(student.student_profile)
            add_message(dialog, student, AuthorRole.STUDENT)
        user = User.objects.get(pk=self.w.sx.pk)
        with self.assertNumQueries(1):
            self.assertEqual(staff_unread_count(user), 6)

    def test_chat_unread_count_by_role(self):
        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(self.bx_dialog, self.w.sx, AuthorRole.STAFF)
        self.assertEqual(chat_unread_count(self.w.sx), 1)
        self.assertEqual(chat_unread_count(self.w.bx), 1)
        self.assertEqual(chat_unread_count(self.w.ax), 0)
        with self.assertNumQueries(0):
            self.assertEqual(chat_unread_count(self.w.root), 0)
            self.assertEqual(chat_unread_count(AnonymousUser()), 0)
