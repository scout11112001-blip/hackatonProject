from datetime import date, timedelta
from unittest import mock

from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from academics.tests.helpers import make_item, make_mark, make_result, make_term
from accounts.models import User
from core.testing import FrozenClockMixin, moscow
from notifications.feed import badge_for_user
from notifications.forms import AnnouncementForm
from notifications.models import Announcement, Audience, NotificationState
from petitions.models import PetitionComment
from petitions.services import change_status
from petitions.tests.helpers import make_petition, make_type
from schedule.models import ChangeKind, LessonChange
from schedule.mutations import save_lesson_change
from schedule.tests.helpers import make_discipline, make_lesson, make_room

from .helpers import make_announcement, make_world, set_seen

NOW = "2026-11-11 12:00"
D = date(2026, 11, 11)


def _query_count(fn) -> int:
    with CaptureQueriesContext(connection) as ctx:
        fn()
    return len(ctx.captured_queries)


class AnnouncementFormTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_choices_only_own_faculty_groups(self):
        form = AnnouncementForm(
            None,
            groups=[self.w.gx1, self.w.gx2],
            today=D,
        )
        choices = dict(form.fields["target"].choices)
        self.assertIn("faculty", choices)
        self.assertIn(f"group-{self.w.gx1.pk}", choices)
        self.assertIn(f"group-{self.w.gx2.pk}", choices)
        self.assertNotIn(f"group-{self.w.gy1.pk}", choices)

    def test_faculty_option_label(self):
        form = AnnouncementForm(
            None,
            groups=[self.w.gx1, self.w.gx2],
            today=D,
        )
        choices = dict(form.fields["target"].choices)
        self.assertEqual(choices["faculty"], "Весь факультет")
        self.assertEqual(choices[f"group-{self.w.gx1.pk}"], "Группа GX1")

    def test_faculty_target(self):
        form = AnnouncementForm(
            {"title": "Заголовок", "body": "Текст", "target": "faculty"},
            groups=[self.w.gx1, self.w.gx2],
            today=D,
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["audience"], Audience.FACULTY)
        self.assertIsNone(form.cleaned_data["group"])

    def test_group_target(self):
        form = AnnouncementForm(
            {"title": "Заголовок", "body": "Текст", "target": f"group-{self.w.gx1.pk}"},
            groups=[self.w.gx1, self.w.gx2],
            today=D,
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["audience"], Audience.GROUP)
        self.assertEqual(form.cleaned_data["group"], self.w.gx1)

    def test_forged_group_rejected(self):
        form = AnnouncementForm(
            {"title": "Заголовок", "body": "Текст", "target": f"group-{self.w.gy1.pk}"},
            groups=[self.w.gx1, self.w.gx2],
            today=D,
        )
        self.assertFalse(form.is_valid())

    def test_university_value_rejected(self):
        form = AnnouncementForm(
            {"title": "Заголовок", "body": "Текст", "target": "university"},
            groups=[self.w.gx1, self.w.gx2],
            today=D,
        )
        self.assertFalse(form.is_valid())

    def test_iso_date_accepted(self):
        form = AnnouncementForm(
            {"title": "Заголовок", "body": "Текст", "target": "faculty", "deadline": "2026-11-20"},
            groups=[self.w.gx1, self.w.gx2],
            today=D,
        )
        self.assertTrue(form.is_valid())

    def test_past_deadline_field_error(self):
        form = AnnouncementForm(
            {"title": "Заголовок", "body": "Текст", "target": "faculty", "deadline": "2026-11-10"},
            groups=[self.w.gx1, self.w.gx2],
            today=D,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("deadline", form.errors)


class FeedAccessTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_anonymous_redirects(self):
        response = self.client.get(reverse("notifications:feed"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/login/?next=/notifications/")

    def test_student_ok(self):
        self.client.force_login(self.w.ax)
        response = self.client.get(reverse("notifications:feed"))
        self.assertEqual(response.status_code, 200)

    def test_staff_forbidden(self):
        self.client.force_login(self.w.sx)
        self.assertEqual(self.client.get(reverse("notifications:feed")).status_code, 403)

    def test_superuser_forbidden(self):
        self.client.force_login(self.w.root)
        self.assertEqual(self.client.get(reverse("notifications:feed")).status_code, 403)

    def test_student_without_profile_forbidden(self):
        user = User.objects.create_user("noprofile", role=User.Role.STUDENT)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("notifications:feed")).status_code, 403)


class StaffAnnouncementsAccessTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_anonymous_get_redirects(self):
        response = self.client.get(reverse("notifications:staff_announcements"))
        self.assertEqual(response.status_code, 302)

    def test_anonymous_post_creates_nothing(self):
        response = self.client.post(
            reverse("notifications:staff_announcements"),
            {"title": "Заголовок", "body": "Текст", "target": "faculty"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Announcement.objects.count(), 0)

    def test_student_get_forbidden(self):
        self.client.force_login(self.w.ax)
        self.assertEqual(
            self.client.get(reverse("notifications:staff_announcements")).status_code, 403
        )

    def test_student_post_forbidden(self):
        self.client.force_login(self.w.ax)
        response = self.client.post(
            reverse("notifications:staff_announcements"),
            {"title": "Заголовок", "body": "Текст", "target": "faculty"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Announcement.objects.count(), 0)

    def test_staff_sees_own_faculty(self):
        make_announcement(
            self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx, title="FX факультет"
        )
        make_announcement(self.w.sx, audience=Audience.GROUP, group=self.w.gx1, title="GX1 группа")
        make_announcement(self.w.sx, audience=Audience.GROUP, group=self.w.gx2, title="GX2 группа")
        self.client.force_login(self.w.sx)
        response = self.client.get(reverse("notifications:staff_announcements"))
        content = response.content.decode()
        self.assertIn("FX факультет", content)
        self.assertIn("GX1 группа", content)
        self.assertIn("GX2 группа", content)

    def test_staff_does_not_see_other_faculty_or_university(self):
        make_announcement(
            self.w.sy, audience=Audience.FACULTY, faculty=self.w.fy, title="FY факультет"
        )
        make_announcement(self.w.sy, audience=Audience.GROUP, group=self.w.gy1, title="GY1 группа")
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY, title="Университет")
        self.client.force_login(self.w.sx)
        response = self.client.get(reverse("notifications:staff_announcements"))
        content = response.content.decode()
        self.assertNotIn("FY факультет", content)
        self.assertNotIn("GY1 группа", content)
        self.assertNotIn("Университет", content)

    def test_superuser_forbidden(self):
        self.client.force_login(self.w.root)
        self.assertEqual(
            self.client.get(reverse("notifications:staff_announcements")).status_code, 403
        )


class StaffUnpublishAccessTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def _post(self, user, announcement):
        self.client.force_login(user)
        return self.client.post(
            reverse("notifications:staff_unpublish", args=[announcement.public_id])
        )

    def test_anonymous(self):
        announcement = make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        response = self.client.post(
            reverse("notifications:staff_unpublish", args=[announcement.public_id])
        )
        self.assertEqual(response.status_code, 302)
        announcement.refresh_from_db()
        self.assertTrue(announcement.is_published)

    def test_student_forbidden(self):
        announcement = make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        response = self._post(self.w.ax, announcement)
        self.assertEqual(response.status_code, 403)
        announcement.refresh_from_db()
        self.assertTrue(announcement.is_published)

    def test_staff_own_faculty_item(self):
        announcement = make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        response = self._post(self.w.sx, announcement)
        self.assertEqual(response.status_code, 302)
        announcement.refresh_from_db()
        self.assertFalse(announcement.is_published)

    def test_staff_own_group_item(self):
        announcement = make_announcement(self.w.sx, audience=Audience.GROUP, group=self.w.gx1)
        response = self._post(self.w.sx, announcement)
        self.assertEqual(response.status_code, 302)
        announcement.refresh_from_db()
        self.assertFalse(announcement.is_published)

    def test_staff_other_faculty_404(self):
        announcement = make_announcement(self.w.sy, audience=Audience.FACULTY, faculty=self.w.fy)
        response = self._post(self.w.sx, announcement)
        self.assertEqual(response.status_code, 404)
        announcement.refresh_from_db()
        self.assertTrue(announcement.is_published)

    def test_staff_university_404(self):
        announcement = make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        response = self._post(self.w.sx, announcement)
        self.assertEqual(response.status_code, 404)

    def test_unknown_uuid_404(self):
        self.client.force_login(self.w.sx)
        response = self.client.post(
            reverse("notifications:staff_unpublish", args=["00000000-0000-0000-0000-000000000000"])
        )
        self.assertEqual(response.status_code, 404)

    def test_superuser_forbidden(self):
        announcement = make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        response = self._post(self.w.root, announcement)
        self.assertEqual(response.status_code, 403)
        announcement.refresh_from_db()
        self.assertTrue(announcement.is_published)

    def test_get_not_allowed(self):
        announcement = make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        self.client.force_login(self.w.sx)
        response = self.client.get(
            reverse("notifications:staff_unpublish", args=[announcement.public_id])
        )
        self.assertEqual(response.status_code, 405)


class HomeSummaryTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_student_summary(self):
        make_announcement(
            self.w.sx, audience=Audience.UNIVERSITY, deadline=D + timedelta(days=1), title="Дедлайн"
        )
        self.client.force_login(self.w.ax)
        response = self.client.get(reverse("core:home"))
        content = response.content.decode()
        self.assertEqual(response.status_code, 200)
        # TASK-012: the home card is titled "Дедлайны" (F6).
        self.assertIn('id="home-deadlines"', content)
        self.assertIn("Дедлайны<span", content)
        self.assertIn("Дедлайн", content)
        self.assertIn("/notifications/#", content)

    def test_limits_to_three(self):
        for i in range(5):
            make_announcement(
                self.w.sx,
                audience=Audience.UNIVERSITY,
                deadline=D + timedelta(days=i + 1),
                title=f"Дедлайн {i}",
            )
            make_announcement(
                self.w.sx,
                audience=Audience.UNIVERSITY,
                published_at=moscow(NOW) - timedelta(hours=i),
                title=f"Новость {i}",
            )
        self.client.force_login(self.w.ax)
        response = self.client.get(reverse("core:home"))
        content = response.content.decode()
        self.assertEqual(content.count("#deadline-"), 3)
        self.assertEqual(content.count("#news-"), 3)

    def test_news_exclude_shown_deadlines(self):
        d1 = make_announcement(
            self.w.sx,
            audience=Audience.UNIVERSITY,
            deadline=D + timedelta(days=1),
            published_at=moscow(NOW) - timedelta(hours=1),
        )
        d2 = make_announcement(
            self.w.sx,
            audience=Audience.UNIVERSITY,
            deadline=D + timedelta(days=2),
            published_at=moscow(NOW) - timedelta(hours=2),
        )
        d3 = make_announcement(
            self.w.sx,
            audience=Audience.UNIVERSITY,
            deadline=D + timedelta(days=3),
            published_at=moscow(NOW) - timedelta(hours=3),
        )
        d4 = make_announcement(
            self.w.sx,
            audience=Audience.UNIVERSITY,
            deadline=D + timedelta(days=4),
            published_at=moscow(NOW) - timedelta(hours=4),
        )
        plain = make_announcement(
            self.w.sx, audience=Audience.UNIVERSITY, published_at=moscow(NOW) - timedelta(hours=5)
        )
        self.client.force_login(self.w.ax)
        content = self.client.get(reverse("core:home")).content.decode()
        before, news_part = content.split('id="home-news"', 1)
        self.assertIn(f"#news-{plain.public_id}", news_part)
        self.assertIn(f"#news-{d4.public_id}", news_part)
        for d in (d1, d2, d3):
            self.assertNotIn(f"#news-{d.public_id}", news_part)
            self.assertIn(f"#deadline-{d.public_id}", before)

    def test_news_without_deadlines_unchanged(self):
        for i in range(4):
            make_announcement(
                self.w.sx,
                audience=Audience.UNIVERSITY,
                published_at=moscow(NOW) - timedelta(hours=i + 1),
            )
        self.client.force_login(self.w.ax)
        content = self.client.get(reverse("core:home")).content.decode()
        news_part = content.split('id="home-news"', 1)[1]
        self.assertEqual(news_part.count("#news-"), 3)

    def test_news_heading(self):
        self.client.force_login(self.w.ax)
        content = self.client.get(reverse("core:home")).content.decode()
        # TASK-012: the card title is a link to the feed anchor (F6).
        self.assertIn(
            '<h2 class="card-title" id="home-news"><a class="card-title-link" '
            'href="/notifications/#feed">Новости<span aria-hidden="true"> →</span></a></h2>',
            content,
        )
        self.assertNotIn("Новости деканата", content)

    def test_student_without_profile(self):
        user = User.objects.create_user("noprof", role=User.Role.STUDENT)
        self.client.force_login(user)
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Раздел в разработке", response.content.decode())

    def test_staff_no_summary(self):
        self.client.force_login(self.w.sx)
        response = self.client.get(reverse("core:home"))
        # TASK-012: staff get the staff home with three buttons (AC9).
        content = response.content.decode()
        self.assertIn("<h1>Деканат</h1>", content)
        self.assertNotIn('id="home-deadlines"', content)

    def test_superuser_no_summary(self):
        self.client.force_login(self.w.root)
        response = self.client.get(reverse("core:home"))
        self.assertIn("Раздел в разработке", response.content.decode())

    def test_home_does_not_mark_read(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        self.client.force_login(self.w.ax)
        self.client.get(reverse("core:home"))
        self.assertFalse(NotificationState.objects.filter(user=self.w.ax).exists())


class CsrfTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.w.sx)

    def test_create_without_token_403(self):
        response = self.client.post(
            reverse("notifications:staff_announcements"),
            {"title": "Заголовок", "body": "Текст", "target": "faculty"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Announcement.objects.count(), 0)

    def test_unpublish_without_token_403(self):
        announcement = make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        response = self.client.post(
            reverse("notifications:staff_unpublish", args=[announcement.public_id])
        )
        self.assertEqual(response.status_code, 403)
        announcement.refresh_from_db()
        self.assertTrue(announcement.is_published)


class FeedViewTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def _get(self):
        self.client.force_login(self.w.ax)
        return self.client.get(reverse("notifications:feed"))

    def test_sections_order(self):
        response = self._get()
        content = response.content.decode()
        self.assertLess(content.find("Ближайшие дедлайны"), content.find("Лента"))

    def test_empty_state(self):
        response = self._get()
        self.assertIn("Уведомлений за последние 30 дней нет.", response.content.decode())

    def test_section_anchors(self):
        content = self._get().content.decode()
        self.assertIn('<section id="deadlines" aria-labelledby="deadlines-title">', content)
        self.assertIn('<section id="feed" aria-labelledby="feed-title">', content)

    def test_change_reason_not_shown(self):
        room = make_room("room-101")
        lesson = make_lesson(
            [self.w.gx1], weekday=2, slot=1, room=room, discipline=make_discipline("Логика")
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 11),
                kind=ChangeKind.CANCELLED,
                reason="Секретная причина",
            )
        )
        content = self._get().content.decode()
        self.assertIn("Отмена занятия: Логика", content)
        self.assertNotIn("Секретная причина", content)

    def test_body_escaped_and_line_breaks_kept(self):
        make_announcement(
            self.w.sx, audience=Audience.UNIVERSITY, body="<b>жирный</b>\nвторая строка"
        )
        content = self._get().content.decode()
        self.assertIn("&lt;b&gt;жирный&lt;/b&gt;", content)
        self.assertIn("<br>", content)
        self.assertNotIn("<b>жирный", content)

    def test_new_marker(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY, title="Свежая")
        content = self._get().content.decode()
        self.assertIn("Новое", content)

    def test_get_marks_read(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        self._get()
        state = NotificationState.objects.get(user=self.w.ax)
        self.assertEqual(state.seen_until, timezone.now())
        content = self._get().content.decode()
        self.assertNotIn("<strong>Новое</strong>", content)

    def test_head_not_allowed(self):
        self.client.force_login(self.w.ax)
        response = self.client.head(reverse("notifications:feed"))
        self.assertEqual(response.status_code, 405)
        self.assertFalse(NotificationState.objects.filter(user=self.w.ax).exists())

    def test_post_not_allowed(self):
        self.client.force_login(self.w.ax)
        response = self.client.post(reverse("notifications:feed"))
        self.assertEqual(response.status_code, 405)

    def test_no_store(self):
        response = self._get()
        self.assertIn("no-store", response["Cache-Control"])


class StaffAnnouncementsViewTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def setUp(self):
        self.client.force_login(self.w.sx)

    def _post(self, data):
        return self.client.post(reverse("notifications:staff_announcements"), data)

    def test_create_faculty_announcement(self):
        response = self._post({"title": "Заголовок", "body": "Текст", "target": "faculty"})
        self.assertEqual(response.status_code, 302)
        announcement = Announcement.objects.get()
        self.assertEqual(announcement.author, self.w.sx)
        self.assertEqual(announcement.faculty, self.w.fx)
        self.assertEqual(announcement.audience, Audience.FACULTY)

    def test_create_group_announcement(self):
        response = self._post(
            {"title": "Заголовок", "body": "Текст", "target": f"group-{self.w.gx1.pk}"}
        )
        self.assertEqual(response.status_code, 302)
        announcement = Announcement.objects.get()
        self.assertEqual(announcement.audience, Audience.GROUP)
        self.assertEqual(announcement.group, self.w.gx1)

    def test_forged_group_form_error(self):
        response = self._post(
            {"title": "Заголовок", "body": "Текст", "target": f"group-{self.w.gy1.pk}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Announcement.objects.count(), 0)

    def test_university_target_form_error(self):
        response = self._post({"title": "Заголовок", "body": "Текст", "target": "university"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Announcement.objects.count(), 0)

    def test_past_deadline_form_error(self):
        response = self._post(
            {"title": "Заголовок", "body": "Текст", "target": "faculty", "deadline": "2026-11-10"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Announcement.objects.count(), 0)

    def test_service_error_shown_as_form_error(self):
        with mock.patch(
            "notifications.views.create_announcement",
            side_effect=__import__(
                "django.core.exceptions", fromlist=["ValidationError"]
            ).ValidationError("x"),
        ):
            response = self._post({"title": "Заголовок", "body": "Текст", "target": "faculty"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].non_field_errors(), ["x"])

    def test_unpublished_shown_with_status_and_no_button(self):
        make_announcement(
            self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx, is_published=False
        )
        response = self.client.get(reverse("notifications:staff_announcements"))
        content = response.content.decode()
        self.assertIn("Снято с публикации", content)
        self.assertNotIn("Снять с публикации", content)

    def test_body_escaped_on_staff_page(self):
        make_announcement(
            self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx, body="<b>жирный</b>"
        )
        response = self.client.get(reverse("notifications:staff_announcements"))
        content = response.content.decode()
        self.assertIn("&lt;b&gt;", content)
        self.assertNotIn("<b>жирный", content)

    def test_student_sees_created_announcement(self):
        self._post({"title": "Заголовок", "body": "Текст", "target": "faculty"})
        self.client.force_login(self.w.ax)
        response = self.client.get(reverse("notifications:feed"))
        self.assertIn("Заголовок", response.content.decode())


class StaffUnpublishViewTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def setUp(self):
        self.client.force_login(self.w.sx)

    def _post(self, announcement):
        return self.client.post(
            reverse("notifications:staff_unpublish", args=[announcement.public_id]), follow=True
        )

    def test_messages(self):
        announcement = make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        first = self._post(announcement)
        self.assertIn("Объявление снято с публикации.", first.content.decode())
        second = self._post(announcement)
        self.assertIn("Объявление уже снято с публикации.", second.content.decode())

    def test_second_post_keeps_unpublished_at(self):
        announcement = make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        self._post(announcement)
        announcement.refresh_from_db()
        first = announcement.unpublished_at
        self._post(announcement)
        announcement.refresh_from_db()
        self.assertEqual(announcement.unpublished_at, first)


class NavTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_student_nav_with_count(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        self.client.force_login(self.w.ax)
        response = self.client.get(reverse("core:home"))
        # TASK-012: the count is the chip of the header button (AC5).
        self.assertIn(
            '<span class="visually-hidden">, непрочитанных: </span>2</span>',
            response.content.decode(),
        )

    def test_student_nav_without_count(self):
        self.client.force_login(self.w.ax)
        response = self.client.get(reverse("core:home"))
        content = response.content.decode()
        self.assertIn("Уведомления", content)
        self.assertNotIn("Уведомления (", content)

    def test_staff_nav_has_announcements(self):
        self.client.force_login(self.w.sx)
        response = self.client.get(reverse("core:home"))
        self.assertIn("Объявления", response.content.decode())

    def test_superuser_nav_has_neither(self):
        self.client.force_login(self.w.root)
        response = self.client.get(reverse("core:home"))
        content = response.content.decode()
        self.assertNotIn("Уведомления", content)
        self.assertNotIn("Объявления", content)


class QueryCountTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def setUp(self):
        self.term = make_term(code="t-2026-autumn")
        self.disc = make_discipline("Дисциплина")
        self.item = make_item(self.w.gx1, self.disc, self.term)
        self.rtype = make_type("Справка")
        self._n = 0

    def _add_feed_batch(self):
        """Add one row of every one of the 6 feed sources for student ax."""
        self._n += 1
        n = self._n
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY, title=f"Новость {n}")
        petition = make_petition(self.w.ax_profile, self.rtype)
        change_status(petition, self.w.sx, "submitted", "in_progress")
        PetitionComment.objects.create(
            petition=petition, author=self.w.sx, text="Комментарий", created_at=timezone.now()
        )
        room = make_room(f"room-{100 + n}")
        lesson = make_lesson([self.w.gx1], weekday=2, slot=n, room=room, discipline=self.disc)
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson, original_date=D, kind=ChangeKind.CANCELLED, reason="Причина"
            )
        )
        make_mark(self.w.ax_profile, self.item, 5, D - timedelta(days=n), "Семинар")
        disc = make_discipline(f"Результат {n}")
        item = make_item(self.w.gx1, disc, self.term)
        make_result(self.w.ax_profile, item, "5", date=D)

    def test_badge_exactly_three_queries(self):
        user = User.objects.get(pk=self.w.ax.pk)
        with self.assertNumQueries(3):
            badge_for_user(user)

    def test_feed_queries_constant(self):
        self.client.force_login(self.w.ax)
        self._add_feed_batch()
        set_seen(self.w.ax, moscow(NOW) - timedelta(days=1))
        count_one = _query_count(lambda: self.client.get(reverse("notifications:feed")))
        for _ in range(4):
            self._add_feed_batch()
        set_seen(self.w.ax, moscow(NOW) - timedelta(days=1))
        count_many = _query_count(lambda: self.client.get(reverse("notifications:feed")))
        self.assertEqual(count_one, count_many)
        self.assertLessEqual(count_one, 20)

    def test_profile_page_counter_constant(self):
        self.client.force_login(self.w.ax)
        zero = _query_count(lambda: self.client.get(reverse("accounts:profile")))
        for _ in range(10):
            make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        ten = _query_count(lambda: self.client.get(reverse("accounts:profile")))
        self.assertEqual(zero, ten)

    def test_staff_list_queries_constant(self):
        make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        self.client.force_login(self.w.sx)
        one = _query_count(lambda: self.client.get(reverse("notifications:staff_announcements")))
        for i in range(3):
            make_announcement(
                self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx, title=f"Факультет {i}"
            )
        make_announcement(self.w.sx, audience=Audience.GROUP, group=self.w.gx1, title="Группа GX1")
        make_announcement(self.w.sx, audience=Audience.GROUP, group=self.w.gx2, title="Группа GX2")
        six = _query_count(lambda: self.client.get(reverse("notifications:staff_announcements")))
        self.assertEqual(one, six)
        self.assertLessEqual(one, 10)

    def test_home_queries_constant(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        self.client.force_login(self.w.ax)
        one = _query_count(lambda: self.client.get(reverse("core:home")))
        for i in range(4):
            make_announcement(self.w.sx, audience=Audience.UNIVERSITY, title=f"Новость {i}")
        five = _query_count(lambda: self.client.get(reverse("core:home")))
        self.assertEqual(one, five)

    def test_home_queries_same_with_deadlines(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        self.client.force_login(self.w.ax)
        count_a = _query_count(lambda: self.client.get(reverse("core:home")))
        for i in range(4):
            make_announcement(
                self.w.sx, audience=Audience.UNIVERSITY, deadline=D + timedelta(days=i + 1)
            )
        for _ in range(3):
            make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        count_b = _query_count(lambda: self.client.get(reverse("core:home")))
        self.assertEqual(count_a, count_b)


class AudienceLabelRenderTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_feed_shows_faculty_name_only(self):
        make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        self.client.force_login(self.w.ax)
        content = self.client.get(reverse("notifications:feed")).content.decode()
        self.assertIn("Факультет FX", content)
        self.assertNotIn("Факультет: ", content)

    def test_staff_list_shows_faculty_name_only(self):
        make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        self.client.force_login(self.w.sx)
        content = self.client.get(reverse("notifications:staff_announcements")).content.decode()
        self.assertIn("Факультет FX", content)
        self.assertNotIn("Факультет: ", content)
