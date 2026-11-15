from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_staff
from core.testing import FrozenClockMixin
from notifications.models import Announcement, Audience

from .helpers import make_announcement


class AnnouncementAdminTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX1")
        cls.staff = make_staff("sx", cls.faculty)
        cls.superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")

    def setUp(self):
        self.client.force_login(self.superuser)

    def test_add_university_announcement_sets_author(self):
        response = self.client.post(
            reverse("admin:notifications_announcement_add"),
            {
                "title": "Новость университета",
                "body": "Текст",
                "audience": Audience.UNIVERSITY,
                "is_published": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        announcement = Announcement.objects.get(title="Новость университета")
        self.assertEqual(announcement.author, self.superuser)
        self.assertTrue(announcement.is_published)

    def test_invalid_combination_shows_error_not_500(self):
        response = self.client.post(
            reverse("admin:notifications_announcement_add"),
            {
                "title": "Без факультета",
                "body": "Текст",
                "audience": Audience.FACULTY,
                "is_published": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Получатели не соответствуют аудитории")
        self.assertFalse(Announcement.objects.filter(title="Без факультета").exists())

    def test_unpublish_in_admin_sets_fields(self):
        announcement = make_announcement(
            self.staff, audience=Audience.FACULTY, faculty=self.faculty
        )
        response = self.client.post(
            reverse("admin:notifications_announcement_change", args=[announcement.pk]),
            {
                "title": announcement.title,
                "body": announcement.body,
                "audience": Audience.FACULTY,
                "faculty": self.faculty.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        announcement.refresh_from_db()
        self.assertFalse(announcement.is_published)
        self.assertEqual(announcement.unpublished_at, timezone.now())
        self.assertEqual(announcement.unpublished_by, self.superuser)

    def test_republish_in_admin_clears_fields(self):
        announcement = make_announcement(
            self.staff, audience=Audience.FACULTY, faculty=self.faculty
        )
        announcement.is_published = False
        announcement.unpublished_at = timezone.now()
        announcement.unpublished_by = self.staff
        announcement.save(update_fields=["is_published", "unpublished_at", "unpublished_by"])
        response = self.client.post(
            reverse("admin:notifications_announcement_change", args=[announcement.pk]),
            {
                "title": announcement.title,
                "body": announcement.body,
                "audience": Audience.FACULTY,
                "faculty": self.faculty.pk,
                "is_published": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        announcement.refresh_from_db()
        self.assertTrue(announcement.is_published)
        self.assertIsNone(announcement.unpublished_at)
        self.assertIsNone(announcement.unpublished_by)
