import re
from unittest import mock

from django.test import TestCase

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from core.testing import FrozenClockMixin
from notifications.feed import badge_for_user
from notifications.models import Audience
from notifications.tests.helpers import make_announcement


def _wide(content: str) -> str:
    start = content.index('<nav class="site-nav site-nav--wide"')
    return content[start : content.index("</nav>", start)]


def _menu(content: str) -> str:
    start = content.index('<details class="site-menu">')
    return content[start : content.index("</details>", start)]


def _hrefs(part: str) -> list[str]:
    return re.findall(r'<a href="([^"]+)"', part)


class NavMarkupTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.student = make_student("stu", cls.group, "REC-1")
        cls.staff = make_staff("stf", cls.faculty)
        cls.superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")

    def test_student_menu(self):
        self.client.force_login(self.student)
        content = self.client.get("/profile/").content.decode()
        self.assertEqual(content.count('<details class="site-menu">'), 1)
        self.assertIn('<summary class="site-menu-toggle">Меню</summary>', content)
        self.assertEqual(_hrefs(_wide(content)), _hrefs(_menu(content)))
        self.assertEqual(
            _hrefs(_wide(content)),
            [
                "/profile/",
                "/schedule/",
                "/map/",
                "/grades/",
                "/requests/",
                # TASK-012: the "Уведомления" item moved to the header button (D11).
                "/chat/",
            ],
        )

    def test_staff_menu(self):
        self.client.force_login(self.staff)
        content = self.client.get("/profile/").content.decode()
        self.assertEqual(_hrefs(_wide(content)), _hrefs(_menu(content)))
        self.assertEqual(
            _hrefs(_wide(content)),
            [
                "/profile/",
                "/staff/schedule/",
                "/map/",
                "/staff/requests/",
                "/staff/chats/",
                "/staff/announcements/",
                "/staff/students/",
            ],
        )

    def test_superuser_menu(self):
        self.client.force_login(self.superuser)
        content = self.client.get("/profile/").content.decode()
        self.assertEqual(_hrefs(_wide(content)), _hrefs(_menu(content)))
        self.assertEqual(_hrefs(_wide(content)), ["/profile/"])

    def test_logout_form_in_both_lists(self):
        self.client.force_login(self.student)
        content = self.client.get("/profile/").content.decode()
        for part in (_wide(content), _menu(content)):
            self.assertIn('<form class="site-nav-logout" method="post" action="/logout/">', part)
            self.assertIn('name="csrfmiddlewaretoken"', part)
        self.client.post("/logout/")
        self.assertEqual(self.client.get("/profile/").status_code, 302)

    def test_current_page_marked(self):
        self.client.force_login(self.student)
        content = self.client.get("/profile/").content.decode()
        self.assertEqual(content.count('href="/profile/" aria-current="page"'), 2)
        self.assertEqual(content.count('aria-current="page"'), 2)

    def test_anonymous_unchanged(self):
        content = self.client.get("/login/").content.decode()
        self.assertNotIn("site-menu", content)
        self.assertNotIn("site-menu-badge", content)
        self.assertIn(
            '<nav class="site-nav site-nav--wide" aria-label="Основная навигация">', content
        )


class NavBadgeTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-11 12:00"

    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.student = make_student("stu", cls.group, "REC-1")
        cls.staff = make_staff("stf", cls.faculty)

    # TASK-012: the "Уведомления (N)" link became the header button with a count chip (AC5, D11).
    def test_notifications_button_with_count(self):
        make_announcement(self.staff, audience=Audience.UNIVERSITY)
        self.client.force_login(self.student)
        content = self.client.get("/profile/").content.decode()
        self.assertIn(
            '<span class="site-notif-count"><span class="visually-hidden">, непрочитанных: '
            "</span>1</span>",
            content,
        )
        button = '<a class="btn site-notif" href="/notifications/">'
        self.assertIn(button, content)
        self.assertGreater(content.index(button), content.index("</details>"))
        self.assertNotIn("site-notif", _wide(content))
        self.assertNotIn("/notifications/", _hrefs(_wide(content)))
        self.assertNotIn("/notifications/", _hrefs(_menu(content)))

    # TASK-012: the button is always shown to students; only the chip depends on the badge.
    def test_no_badge_without_unread(self):
        self.client.force_login(self.student)
        content = self.client.get("/profile/").content.decode()
        self.assertIn('class="btn site-notif"', content)
        self.assertNotIn("site-notif-count", content)

    # TASK-012: staff have no notifications button (AC6).
    def test_no_badge_for_staff(self):
        make_announcement(self.staff, audience=Audience.UNIVERSITY)
        self.client.force_login(self.staff)
        content = self.client.get("/profile/").content.decode()
        self.assertNotIn("site-notif", content)

    def test_no_button_for_superuser_and_anonymous(self):
        superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")
        self.client.force_login(superuser)
        self.assertNotIn("site-notif", self.client.get("/profile/").content.decode())
        self.client.logout()
        self.assertNotIn("site-notif", self.client.get("/login/").content.decode())

    def test_button_current_on_feed(self):
        self.client.force_login(self.student)
        content = self.client.get("/notifications/").content.decode()
        self.assertIn(
            '<a class="btn site-notif" href="/notifications/" aria-current="page">', content
        )
        self.assertEqual(content.count('aria-current="page"'), 1)

    def test_badge_cap_label(self):
        self.client.force_login(self.student)
        with mock.patch(
            "notifications.templatetags.notifications_tags.badge_for_user", return_value="50+"
        ):
            content = self.client.get("/profile/").content.decode()
        self.assertIn('<span class="visually-hidden">, непрочитанных: </span>50+</span>', content)

    def test_badge_computed_once(self):
        make_announcement(self.staff, audience=Audience.UNIVERSITY)
        self.client.force_login(self.student)
        with mock.patch(
            "notifications.templatetags.notifications_tags.badge_for_user",
            wraps=badge_for_user,
        ) as spy:
            self.client.get("/profile/")
        self.assertEqual(spy.call_count, 1)
