from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from core.testing import FrozenClockMixin, moscow
from notifications.constants import TITLE_MAX_LENGTH
from notifications.models import Announcement, Audience, NotificationState
from notifications.selectors import announcements_managed_by
from notifications.services import (
    create_announcement,
    deadline_errors,
    mark_seen,
    unpublish_announcement,
)

from .helpers import make_announcement, make_world, set_seen

NOW = "2026-11-11 12:00"


class ManagedBySelectorTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_staff_sees_faculty_and_group_items(self):
        make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        make_announcement(self.w.sx, audience=Audience.GROUP, group=self.w.gx1)
        make_announcement(self.w.sx, audience=Audience.GROUP, group=self.w.gx2)
        ids = set(announcements_managed_by(self.w.sx).values_list("id", flat=True))
        self.assertEqual(len(ids), 3)

    def test_staff_does_not_see_other_faculty(self):
        make_announcement(self.w.sy, audience=Audience.FACULTY, faculty=self.w.fy)
        make_announcement(self.w.sy, audience=Audience.GROUP, group=self.w.gy1)
        self.assertFalse(announcements_managed_by(self.w.sx).exists())

    def test_staff_does_not_see_university(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        self.assertFalse(announcements_managed_by(self.w.sx).exists())

    def test_student_and_superuser_get_none(self):
        make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        self.assertFalse(announcements_managed_by(self.w.ax).exists())
        self.assertFalse(announcements_managed_by(self.w.root).exists())

    def test_staff_without_profile_gets_none(self):
        user = User.objects.create_user("noprofile", role=User.Role.STAFF)
        make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        self.assertFalse(announcements_managed_by(user).exists())

    def test_inactive_staff_gets_none(self):
        make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        self.w.sx.is_active = False
        self.w.sx.save(update_fields=["is_active"])
        self.assertFalse(announcements_managed_by(self.w.sx).exists())


class DeadlineErrorsTests(TestCase):
    def test_none_ok(self):
        self.assertEqual(deadline_errors(None, moscow(NOW).date()), [])

    def test_today_ok(self):
        self.assertEqual(deadline_errors(moscow(NOW).date(), moscow(NOW).date()), [])

    def test_yesterday_error(self):
        self.assertEqual(
            deadline_errors(moscow(NOW).date() - timedelta(days=1), moscow(NOW).date()),
            ["Срок не может быть в прошлом."],
        )

    def test_max_ahead_ok(self):
        self.assertEqual(
            deadline_errors(moscow(NOW).date() + timedelta(days=365), moscow(NOW).date()), []
        )

    def test_beyond_max_error(self):
        self.assertEqual(
            deadline_errors(moscow(NOW).date() + timedelta(days=366), moscow(NOW).date()),
            ["Срок — не позже чем через 365 дней."],
        )


class CreateAnnouncementTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_faculty_announcement(self):
        announcement = create_announcement(
            self.w.sx,
            title="Заголовок",
            body="Текст",
            audience=Audience.FACULTY,
            group=None,
            deadline=None,
        )
        self.assertEqual(announcement.faculty, self.w.fx)
        self.assertIsNone(announcement.group)
        self.assertEqual(announcement.author, self.w.sx)
        self.assertEqual(announcement.published_at, timezone.now())
        self.assertTrue(announcement.is_published)

    def test_own_group_announcement(self):
        announcement = create_announcement(
            self.w.sx,
            title="Заголовок",
            body="Текст",
            audience=Audience.GROUP,
            group=self.w.gx1,
            deadline=None,
        )
        self.assertIsNone(announcement.faculty)
        self.assertEqual(announcement.group, self.w.gx1)

    def test_other_faculty_group_rejected(self):
        with self.assertRaises(ValidationError):
            create_announcement(
                self.w.sx,
                title="Заголовок",
                body="Текст",
                audience=Audience.GROUP,
                group=self.w.gy1,
                deadline=None,
            )
        self.assertEqual(Announcement.objects.count(), 0)

    def test_university_rejected(self):
        with self.assertRaises(ValidationError):
            create_announcement(
                self.w.sx,
                title="Заголовок",
                body="Текст",
                audience=Audience.UNIVERSITY,
                group=None,
                deadline=None,
            )
        self.assertEqual(Announcement.objects.count(), 0)

    def test_group_without_group_rejected(self):
        with self.assertRaises(ValidationError):
            create_announcement(
                self.w.sx,
                title="Заголовок",
                body="Текст",
                audience=Audience.GROUP,
                group=None,
                deadline=None,
            )
        self.assertEqual(Announcement.objects.count(), 0)

    def test_past_deadline_rejected(self):
        with self.assertRaises(ValidationError):
            create_announcement(
                self.w.sx,
                title="Заголовок",
                body="Текст",
                audience=Audience.FACULTY,
                group=None,
                deadline=moscow(NOW).date() - timedelta(days=1),
            )

    def test_deadline_today_ok(self):
        announcement = create_announcement(
            self.w.sx,
            title="Заголовок",
            body="Текст",
            audience=Audience.FACULTY,
            group=None,
            deadline=moscow(NOW).date(),
        )
        self.assertEqual(announcement.deadline, moscow(NOW).date())

    def test_too_long_title_rejected(self):
        with self.assertRaises(ValidationError):
            create_announcement(
                self.w.sx,
                title="а" * (TITLE_MAX_LENGTH + 1),
                body="Текст",
                audience=Audience.FACULTY,
                group=None,
                deadline=None,
            )

    def test_student_author_denied(self):
        with self.assertRaises(PermissionDenied):
            create_announcement(
                self.w.ax,
                title="Заголовок",
                body="Текст",
                audience=Audience.FACULTY,
                group=None,
                deadline=None,
            )

    def test_superuser_author_denied(self):
        with self.assertRaises(PermissionDenied):
            create_announcement(
                self.w.root,
                title="Заголовок",
                body="Текст",
                audience=Audience.FACULTY,
                group=None,
                deadline=None,
            )


class UnpublishTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_unpublish_own_faculty(self):
        announcement = make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        self.assertTrue(unpublish_announcement(self.w.sx, announcement.public_id))
        announcement.refresh_from_db()
        self.assertFalse(announcement.is_published)
        self.assertEqual(announcement.unpublished_at, timezone.now())
        self.assertEqual(announcement.unpublished_by, self.w.sx)

    def test_unpublish_own_group_item(self):
        announcement = make_announcement(self.w.sx, audience=Audience.GROUP, group=self.w.gx1)
        self.assertTrue(unpublish_announcement(self.w.sx, announcement.public_id))

    def test_second_call_is_noop(self):
        announcement = make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        self.assertTrue(unpublish_announcement(self.w.sx, announcement.public_id))
        announcement.refresh_from_db()
        first = announcement.unpublished_at
        self.assertFalse(unpublish_announcement(self.w.sx, announcement.public_id))
        announcement.refresh_from_db()
        self.assertEqual(announcement.unpublished_at, first)

    def test_other_faculty_raises_does_not_exist(self):
        announcement = make_announcement(self.w.sy, audience=Audience.FACULTY, faculty=self.w.fy)
        with self.assertRaises(Announcement.DoesNotExist):
            unpublish_announcement(self.w.sx, announcement.public_id)

    def test_university_raises_does_not_exist(self):
        announcement = make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        with self.assertRaises(Announcement.DoesNotExist):
            unpublish_announcement(self.w.sx, announcement.public_id)

    def test_student_denied(self):
        announcement = make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        with self.assertRaises(PermissionDenied):
            unpublish_announcement(self.w.ax, announcement.public_id)


class MarkSeenTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_creates_state(self):
        mark_seen(self.w.ax.pk, timezone.now())
        state = NotificationState.objects.get(user=self.w.ax)
        self.assertEqual(state.seen_until, timezone.now())

    def test_moves_forward(self):
        set_seen(self.w.ax, timezone.now() - timedelta(hours=1))
        mark_seen(self.w.ax.pk, timezone.now())
        self.assertEqual(NotificationState.objects.get(user=self.w.ax).seen_until, timezone.now())

    def test_never_moves_back(self):
        future = timezone.now() + timedelta(hours=1)
        set_seen(self.w.ax, future)
        mark_seen(self.w.ax.pk, timezone.now())
        self.assertEqual(NotificationState.objects.get(user=self.w.ax).seen_until, future)

    def test_null_state_is_set(self):
        NotificationState.objects.create(user=self.w.ax, seen_until=None)
        mark_seen(self.w.ax.pk, timezone.now())
        self.assertEqual(NotificationState.objects.get(user=self.w.ax).seen_until, timezone.now())
