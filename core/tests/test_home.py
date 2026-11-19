"""Home page for students, staff and other roles (TASK-012, AC7-AC10, AC12)."""

import re
from datetime import date

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from chat.models import AuthorRole
from chat.tests.helpers import add_message, make_dialog
from core.testing import FrozenClockMixin, moscow
from notifications.models import Audience
from notifications.tests.helpers import make_announcement
from schedule.models import ChangeKind, LessonChange
from schedule.mutations import save_lesson_change
from schedule.tests.helpers import make_discipline, make_lesson, make_room

TODAY = date(2026, 11, 11)


def _home_world(cls) -> None:
    cls.faculty = make_faculty("FX")
    cls.group = make_group(cls.faculty, "GX")
    cls.other_group = make_group(cls.faculty, "GY")
    cls.student = make_student("stu", cls.group, "REC-1")
    cls.staff = make_staff("stf", cls.faculty)
    cls.superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")
    cls.noprof = User.objects.create_user("noprof", role=User.Role.STUDENT)
    cls.room_101 = make_room("room-101")
    cls.room_102 = make_room("room-102")
    cls.room_103 = make_room("room-103")
    cls.lesson_a = make_lesson(
        [cls.group],
        weekday=2,
        slot=1,
        room=cls.room_101,
        discipline=make_discipline("Английский язык"),
        lesson_type="seminar",
    )
    cls.lesson_b = make_lesson(
        [cls.group],
        weekday=2,
        slot=2,
        room=cls.room_102,
        discipline=make_discipline("Микроэкономика"),
    )
    save_lesson_change(
        LessonChange(
            weekly_lesson=cls.lesson_b,
            original_date=TODAY,
            kind=ChangeKind.ROOM_CHANGED,
            new_room=cls.room_103,
            reason="Ремонт",
        )
    )
    cls.lesson_c = make_lesson(
        [cls.other_group],
        weekday=2,
        slot=3,
        room=cls.room_101,
        discipline=make_discipline("Чужая дисциплина"),
    )


class HomeStudentTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-11 11:00"

    @classmethod
    def setUpTestData(cls):
        _home_world(cls)

    def _content(self) -> str:
        self.client.force_login(self.student)
        return self.client.get("/").content.decode()

    def test_student_home_cards(self):
        self.client.force_login(self.student)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("<h1>Сегодня</h1>", content)
        self.assertIn('<p class="page-sub">Среда, 11 ноября · GX</p>', content)
        lessons = content.index('id="home-lessons"')
        deadlines = content.index('id="home-deadlines"')
        news = content.index('id="home-news"')
        self.assertLess(lessons, deadlines)
        self.assertLess(deadlines, news)
        docs = content.index('<a class="btn" href="/requests/">Документы</a>')
        chat = content.index('<a class="btn" href="/chat/">Чат</a>')
        self.assertLess(news, docs)
        self.assertLess(docs, chat)

    def test_lessons_card(self):
        self.client.force_login(self.student)
        response = self.client.get("/")
        content = response.content.decode()
        self.assertEqual(len(response.context["annotation"].rows), 2)
        self.assertIn("Английский язык", content)
        self.assertIn("Микроэкономика", content)
        tag = '<span class="tag">идёт</span>'
        self.assertEqual(content.count(tag), 1)
        self.assertGreater(content.index(tag), content.index("10:40"))
        self.assertIn('href="/map/room/room-103/">ауд. 103</a>', content)
        self.assertIn('<span class="lesson-change">аудитория изменена</span>', content)

    def test_lessons_card_hides_reason(self):
        save_lesson_change(
            LessonChange(
                weekly_lesson=self.lesson_a,
                original_date=TODAY,
                kind=ChangeKind.CANCELLED,
                reason="Болезнь",
            )
        )
        content = self._content()
        self.assertIn("отменено", content)
        self.assertNotIn("Ремонт", content)
        self.assertNotIn("Болезнь", content)

    def test_lesson_meta_separator_glued(self):
        content = self._content()
        metas = re.findall(r'<p class="lesson-meta">(.*?)</p>', content, re.S)
        self.assertEqual(len(metas), 2)
        for meta in metas:
            self.assertIn("&nbsp;· ", meta)
            self.assertIsNone(re.search(r"[ \t\n]·", meta))

    def test_other_group_lessons_hidden(self):
        self.assertNotIn("Чужая дисциплина", self._content())

    def test_cancelled_lesson_not_linked(self):
        save_lesson_change(
            LessonChange(
                weekly_lesson=self.lesson_a,
                original_date=TODAY,
                kind=ChangeKind.CANCELLED,
                reason="Болезнь",
            )
        )
        content = self._content()
        start = content.index("Английский язык")
        row = content[start : content.index("</li>", start)]
        self.assertIn('<span class="room">ауд. 101</span>', row)
        self.assertIn("отменено", row)
        self.assertNotIn("/map/room/room-101/", content)

    def test_card_titles_link_to_feed_anchors(self):
        content = self._content()
        self.assertIn(
            '<a class="card-title-link" href="/notifications/#deadlines">'
            'Дедлайны<span aria-hidden="true"> →</span></a>',
            content,
        )
        self.assertIn(
            '<a class="card-title-link" href="/notifications/#feed">'
            'Новости<span aria-hidden="true"> →</span></a>',
            content,
        )

    def test_deadline_row_markup(self):
        title = ("Длинный заголовок дедлайна " * 6)[:150]
        self.assertEqual(len(title), 150)
        a = make_announcement(
            self.staff, audience=Audience.UNIVERSITY, title=title, deadline=date(2026, 11, 12)
        )
        content = self._content()
        self.assertIn(
            f'<li class="card-row"><a class="card-row-title" '
            f'href="/notifications/#deadline-{a.public_id}" title="{title}">{title}</a>'
            f'<time class="card-row-label card-row-label--deadline" datetime="2026-11-12">'
            f"завтра</time></li>",
            content,
        )

    def test_news_row_markup(self):
        make_announcement(
            self.staff,
            audience=Audience.UNIVERSITY,
            title="Новость дня",
            published_at=moscow("2026-11-10 10:00"),
        )
        content = self._content()
        self.assertIn('title="Новость дня">Новость дня</a>', content)
        self.assertIn(
            '<time class="card-row-label" datetime="2026-11-10T10:00:00+03:00">10.11</time>',
            content,
        )

    def test_empty_cards(self):
        content = self._content()
        self.assertIn('<p class="card-empty">Ближайших дедлайнов нет.</p>', content)
        self.assertIn('<p class="card-empty">Новостей пока нет.</p>', content)

    def test_all_notifications_link_removed(self):
        self.assertNotIn("Все уведомления", self._content())


class HomeNoLessonsTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-15 11:00"

    @classmethod
    def setUpTestData(cls):
        _home_world(cls)

    def test_no_lessons_empty_state(self):
        self.client.force_login(self.student)
        content = self.client.get("/").content.decode()
        self.assertIn('<p class="card-empty">Сегодня занятий нет.</p>', content)
        self.assertNotIn("lesson-list--compact", content)


class HomeOtherRolesTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-11 11:00"

    @classmethod
    def setUpTestData(cls):
        _home_world(cls)

    def test_staff_home_buttons(self):
        self.client.force_login(self.staff)
        content = self.client.get("/").content.decode()
        self.assertIn("<h1>Деканат</h1>", content)
        requests = content.index('<a class="btn" href="/staff/requests/">Заявки</a>')
        chats = content.index('<a class="btn" href="/staff/chats/">Чаты</a>')
        ann = content.index('<a class="btn" href="/staff/announcements/">Объявления</a>')
        self.assertLess(requests, chats)
        self.assertLess(chats, ann)
        self.assertNotIn('id="home-lessons"', content)

    def _assert_placeholder(self, user):
        self.client.force_login(user)
        content = self.client.get("/").content.decode()
        self.assertIn("Раздел в разработке", content)
        main = content[content.index("<main") :]
        self.assertNotIn('class="btn"', main)

    def test_superuser_placeholder(self):
        self._assert_placeholder(self.superuser)

    def test_student_without_profile_placeholder(self):
        self._assert_placeholder(self.noprof)


class HomeQueryTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-11 11:00"

    @classmethod
    def setUpTestData(cls):
        _home_world(cls)
        make_announcement(cls.staff, audience=Audience.UNIVERSITY, title="Новость")
        dialog = make_dialog(cls.student.student_profile)
        add_message(dialog, cls.staff, AuthorRole.STAFF, created_at=moscow("2026-11-11 10:00"))

    def setUp(self):
        self.client.force_login(self.student)

    def _count(self) -> int:
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        return len(ctx.captured_queries)

    def test_exact_queries(self):
        make_announcement(
            self.staff, audience=Audience.UNIVERSITY, title="Дедлайн", deadline=date(2026, 11, 13)
        )
        with self.assertNumQueries(14):
            self.client.get("/")

    def test_queries_constant_in_lessons(self):
        self.lesson_a.delete()
        one = self._count()
        make_lesson([self.group], weekday=2, slot=1, room=self.room_101)
        make_lesson([self.group], weekday=2, slot=4, room=self.room_102)
        self.assertEqual(self._count(), one)

    def test_queries_constant_in_deadlines(self):
        none = self._count()
        for day in range(12, 16):
            make_announcement(
                self.staff,
                audience=Audience.UNIVERSITY,
                title=f"Дедлайн {day}",
                deadline=date(2026, 11, day),
            )
        self.assertEqual(self._count(), none)
