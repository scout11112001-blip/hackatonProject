import os
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from academics.models import CurrentMark
from accounts.models import User
from core.testing import FrozenClockMixin
from notifications.feed import badge_for_user, build_feed, student_context, upcoming_deadlines
from notifications.models import Announcement, Audience
from notifications.selectors import announcements_managed_by
from petitions.models import Petition, PetitionComment

PASSWORD = "Local-Demo-Pass-2026!"


class NotificationsSeedTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-22 12:00"

    def _seed(self):
        out = StringIO()
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": PASSWORD}):
            call_command("seed_demo", stdout=out)
        return out.getvalue()

    def test_creates_nine_announcements(self):
        self._seed()
        self.assertEqual(Announcement.objects.count(), 9)
        self.assertEqual(Announcement.objects.filter(is_published=False).count(), 2)
        self.assertEqual(Announcement.objects.filter(audience=Audience.UNIVERSITY).count(), 2)
        self.assertEqual(Announcement.objects.filter(audience=Audience.FACULTY).count(), 5)
        self.assertEqual(Announcement.objects.filter(audience=Audience.GROUP).count(), 2)

    def test_idempotent(self):
        self._seed()
        output = self._seed()
        self.assertEqual(Announcement.objects.count(), 9)
        self.assertIn("Notifications ready: 0 announcements.", output)

    def test_deadlines_in_jury_window(self):
        self._seed()
        deadlines = list(
            Announcement.objects.filter(
                is_published=True, deadline__gte=timezone.localdate()
            ).values_list("deadline", flat=True)
        )
        self.assertGreaterEqual(len(deadlines), 4)
        for deadline in deadlines:
            self.assertGreaterEqual(deadline.year, 2026)
            self.assertIn(deadline.month, (11,))
            self.assertGreaterEqual(deadline.day, 23)
            self.assertLessEqual(deadline.day, 28)

    def test_every_demo_student_has_unread_and_deadlines(self):
        self._seed()
        for username in ("student1", "student2", "student3"):
            student = User.objects.get(username=username)
            self.assertNotEqual(badge_for_user(student), "")
            ctx = student_context(student)
            self.assertTrue(upcoming_deadlines(ctx, 10))

    def test_staff_lists_include_unpublished(self):
        self._seed()
        staff1 = User.objects.get(username="staff1")
        staff2 = User.objects.get(username="staff2")
        for staff in (staff1, staff2):
            self.assertTrue(announcements_managed_by(staff).filter(is_published=False).exists())

    def test_seeded_marks_recorded_on_their_date(self):
        self._seed()
        for mark in CurrentMark.objects.exclude(seed_key=""):
            self.assertEqual(timezone.localtime(mark.created_at).date(), mark.date)
            self.assertLessEqual(mark.created_at, timezone.now())

    def test_previous_term_results_not_in_feed(self):
        self._seed()
        student = User.objects.get(username="student1")
        items = build_feed(student_context(student))
        self.assertFalse(any(i.kind == "final_result" for i in items))

    def test_seeded_staff_comment_time_is_explicit(self):
        self._seed()
        petition = Petition.objects.get(seed_key="p-2")
        comment = PetitionComment.objects.get(petition=petition)
        self.assertEqual(comment.created_at, petition.created_at + timedelta(hours=40))
