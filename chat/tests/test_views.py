"""View tests for the chat app."""

import uuid

from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.models import User
from accounts.tests.helpers import make_student
from chat.constants import RATE_LIMIT_MESSAGES
from chat.models import AuthorRole, Dialog, Message
from chat.selectors import student_unread_count
from chat.tests.helpers import add_message, make_dialog
from core.testing import FrozenClockMixin
from notifications.feed import badge_for_user
from notifications.tests.helpers import make_world

NOW = "2026-11-11 12:00"


def _query_count(fn) -> int:
    with CaptureQueriesContext(connection) as ctx:
        fn()
    return len(ctx.captured_queries)


class _ChatWorld(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.ax_dialog = make_dialog(cls.w.ax_profile)
        cls.bx_dialog = make_dialog(cls.w.bx_profile)
        cls.ay_dialog = make_dialog(cls.w.ay_profile)
        add_message(cls.ax_dialog, cls.w.ax, AuthorRole.STUDENT, text="ax text")
        add_message(cls.bx_dialog, cls.w.bx, AuthorRole.STUDENT, text="bx text")
        add_message(cls.ay_dialog, cls.w.ay, AuthorRole.STUDENT, text="ay text")
        cls.ax_uuid = cls.ax_dialog.public_id
        cls.np = User.objects.create_user(username="np", role=User.Role.STUDENT)


class AccessTests(_ChatWorld):
    def _post_data(self):
        return {"text": "Привет", "client_token": str(uuid.uuid4())}

    def test_student_page_anonymous(self):
        self.assertEqual(self.client.get("/chat/").status_code, 302)

    def test_student_page_student(self):
        self.client.force_login(self.w.ax)
        response = self.client.get("/chat/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("ax text", content)
        self.assertNotIn("bx text", content)

    def test_student_page_staff(self):
        self.client.force_login(self.w.sx)
        self.assertEqual(self.client.get("/chat/").status_code, 403)

    def test_student_page_other_staff(self):
        self.client.force_login(self.w.sy)
        self.assertEqual(self.client.get("/chat/").status_code, 403)

    def test_student_page_superuser(self):
        self.client.force_login(self.w.root)
        self.assertEqual(self.client.get("/chat/").status_code, 403)

    def test_student_updates_anonymous(self):
        self.assertEqual(self.client.get("/chat/updates/?after=0").status_code, 302)

    def test_student_updates_student(self):
        self.client.force_login(self.w.ax)
        response = self.client.get("/chat/updates/?after=0")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("ax text", content)
        self.assertNotIn("bx text", content)

    def test_student_updates_staff(self):
        self.client.force_login(self.w.sx)
        self.assertEqual(self.client.get("/chat/updates/?after=0").status_code, 403)

    def test_student_updates_superuser(self):
        self.client.force_login(self.w.root)
        self.assertEqual(self.client.get("/chat/updates/?after=0").status_code, 403)

    def test_student_post_anonymous(self):
        before = Message.objects.count()
        self.assertEqual(self.client.post("/chat/", self._post_data()).status_code, 302)
        self.assertEqual(Message.objects.count(), before)

    def test_student_post_student(self):
        self.client.force_login(self.w.ax)
        before = Message.objects.filter(dialog=self.ax_dialog).count()
        response = self.client.post("/chat/", self._post_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Message.objects.filter(dialog=self.ax_dialog).count(), before + 1)

    def test_student_post_staff(self):
        self.client.force_login(self.w.sx)
        before = Message.objects.count()
        self.assertEqual(self.client.post("/chat/", self._post_data()).status_code, 403)
        self.assertEqual(Message.objects.count(), before)

    def test_student_post_superuser(self):
        self.client.force_login(self.w.root)
        before = Message.objects.count()
        self.assertEqual(self.client.post("/chat/", self._post_data()).status_code, 403)
        self.assertEqual(Message.objects.count(), before)

    def test_staff_list_anonymous(self):
        self.assertEqual(self.client.get("/staff/chats/").status_code, 302)

    def test_staff_list_student(self):
        self.client.force_login(self.w.ax)
        self.assertEqual(self.client.get("/staff/chats/").status_code, 403)

    def test_staff_list_staff(self):
        self.client.force_login(self.w.sx)
        response = self.client.get("/staff/chats/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'href="/staff/chats/{self.ax_uuid}/"', content)
        self.assertIn(f'href="/staff/chats/{self.bx_dialog.public_id}/"', content)
        self.assertNotIn(f'href="/staff/chats/{self.ay_dialog.public_id}/"', content)

    def test_staff_list_other_staff(self):
        self.client.force_login(self.w.sy)
        response = self.client.get("/staff/chats/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'href="/staff/chats/{self.ay_dialog.public_id}/"', content)
        self.assertNotIn(f'href="/staff/chats/{self.ax_uuid}/"', content)

    def test_staff_list_superuser(self):
        self.client.force_login(self.w.root)
        self.assertEqual(self.client.get("/staff/chats/").status_code, 403)

    def test_staff_dialog_anonymous(self):
        self.assertEqual(self.client.get(f"/staff/chats/{self.ax_uuid}/").status_code, 302)

    def test_staff_dialog_student(self):
        self.client.force_login(self.w.ax)
        self.assertEqual(self.client.get(f"/staff/chats/{self.ax_uuid}/").status_code, 403)

    def test_staff_dialog_staff(self):
        self.client.force_login(self.w.sx)
        response = self.client.get(f"/staff/chats/{self.ax_uuid}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ax text", response.content.decode())

    def test_staff_dialog_other_faculty_404(self):
        self.client.force_login(self.w.sy)
        self.assertEqual(self.client.get(f"/staff/chats/{self.ax_uuid}/").status_code, 404)

    def test_staff_dialog_superuser(self):
        self.client.force_login(self.w.root)
        self.assertEqual(self.client.get(f"/staff/chats/{self.ax_uuid}/").status_code, 403)

    def test_staff_updates_anonymous(self):
        self.assertEqual(
            self.client.get(f"/staff/chats/{self.ax_uuid}/updates/?after=0").status_code, 302
        )

    def test_staff_updates_student(self):
        self.client.force_login(self.w.ax)
        self.assertEqual(
            self.client.get(f"/staff/chats/{self.ax_uuid}/updates/?after=0").status_code, 403
        )

    def test_staff_updates_staff(self):
        self.client.force_login(self.w.sx)
        response = self.client.get(f"/staff/chats/{self.ax_uuid}/updates/?after=0")
        self.assertEqual(response.status_code, 200)

    def test_staff_updates_other_faculty_404(self):
        self.client.force_login(self.w.sy)
        self.assertEqual(
            self.client.get(f"/staff/chats/{self.ax_uuid}/updates/?after=0").status_code, 404
        )

    def test_staff_updates_superuser(self):
        self.client.force_login(self.w.root)
        self.assertEqual(
            self.client.get(f"/staff/chats/{self.ax_uuid}/updates/?after=0").status_code, 403
        )

    def test_staff_post_anonymous(self):
        before = Message.objects.count()
        self.assertEqual(
            self.client.post(f"/staff/chats/{self.ax_uuid}/", self._post_data()).status_code, 302
        )
        self.assertEqual(Message.objects.count(), before)

    def test_staff_post_student(self):
        self.client.force_login(self.w.ax)
        before = Message.objects.count()
        self.assertEqual(
            self.client.post(f"/staff/chats/{self.ax_uuid}/", self._post_data()).status_code, 403
        )
        self.assertEqual(Message.objects.count(), before)

    def test_staff_post_staff(self):
        self.client.force_login(self.w.sx)
        before = Message.objects.filter(dialog=self.ax_dialog).count()
        response = self.client.post(f"/staff/chats/{self.ax_uuid}/", self._post_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Message.objects.filter(dialog=self.ax_dialog).count(), before + 1)
        last = Message.objects.filter(dialog=self.ax_dialog).latest("id")
        self.assertEqual(last.author_role, AuthorRole.STAFF)

    def test_staff_post_other_faculty_404(self):
        self.client.force_login(self.w.sy)
        before = Message.objects.count()
        self.assertEqual(
            self.client.post(f"/staff/chats/{self.ax_uuid}/", self._post_data()).status_code, 404
        )
        self.assertEqual(Message.objects.count(), before)

    def test_staff_post_superuser(self):
        self.client.force_login(self.w.root)
        before = Message.objects.count()
        self.assertEqual(
            self.client.post(f"/staff/chats/{self.ax_uuid}/", self._post_data()).status_code, 403
        )
        self.assertEqual(Message.objects.count(), before)

    def test_unknown_uuid_staff_404(self):
        self.client.force_login(self.w.sx)
        self.assertEqual(self.client.get(f"/staff/chats/{uuid.uuid4()}/").status_code, 404)

    def test_student_page_without_profile_403(self):
        self.client.force_login(self.np)
        self.assertEqual(self.client.get("/chat/").status_code, 403)

    def test_updates_method_not_allowed(self):
        self.client.force_login(self.w.ax)
        self.assertEqual(self.client.head("/chat/updates/?after=0").status_code, 405)
        self.assertEqual(self.client.post("/chat/updates/?after=0").status_code, 405)


class CsrfTests(_ChatWorld):
    def test_student_post_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.w.ax)
        before = Message.objects.count()
        self.assertEqual(client.post("/chat/", {"text": "Привет"}).status_code, 403)
        self.assertEqual(Message.objects.count(), before)

    def test_staff_post_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.w.sx)
        before = Message.objects.count()
        self.assertEqual(
            client.post(f"/staff/chats/{self.ax_uuid}/", {"text": "Привет"}).status_code, 403
        )
        self.assertEqual(Message.objects.count(), before)


class ViewTests(_ChatWorld):
    def test_student_page_without_dialog(self):
        self.client.force_login(self.w.cx)
        response = self.client.get("/chat/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Сообщений пока нет.", content)
        self.assertIn('id="chat-form"', content)
        self.assertFalse(Dialog.objects.filter(student=self.w.cx_profile).exists())

    def test_student_page_layout(self):
        dialog = self.ax_dialog
        a = add_message(dialog, self.w.ax, AuthorRole.STUDENT, text="первое")
        b = add_message(dialog, self.w.sx, AuthorRole.STAFF, text="второе")
        self.client.force_login(self.w.ax)
        content = self.client.get("/chat/").content.decode()
        # Oldest first: a before b.
        self.assertLess(
            content.index(f'data-message-id="{a.pk}"'),
            content.index(f'data-message-id="{b.pk}"'),
        )
        # The form is after the last message.
        self.assertGreater(
            content.index('id="chat-form"'), content.index(f'data-message-id="{b.pk}"')
        )
        self.assertIn(">Вы</strong>", content)
        self.assertIn("Деканат ·", content)

    def test_text_escaped_line_breaks_kept(self):
        dialog = self.ax_dialog
        add_message(dialog, self.w.ax, AuthorRole.STUDENT, text="<b>x</b>\nстрока")
        self.client.force_login(self.w.ax)
        content = self.client.get("/chat/").content.decode()
        self.assertIn("&lt;b&gt;x&lt;/b&gt;<br>строка", content)

    def test_page_has_refresh_link_and_plain_form(self):
        self.client.force_login(self.w.ax)
        content = self.client.get("/chat/").content.decode()
        self.assertIn('<a href="/chat/">Обновить</a>', content)
        self.assertIn(
            '<form method="post" class="form chat-form" id="chat-form" action="/chat/">', content
        )
        self.assertIn('name="csrfmiddlewaretoken"', content)
        self.assertIn('name="client_token"', content)

    def test_script_is_external_and_deferred(self):
        self.client.force_login(self.w.ax)
        content = self.client.get("/chat/").content.decode()
        self.assertIn('<script src="/static/js/chat.js" defer></script>', content)
        self.assertNotIn("<script>", content)

    def test_post_redirects_to_form_anchor(self):
        self.client.force_login(self.w.ax)
        response = self.client.post("/chat/", {"text": "Привет"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].endswith("/chat/#chat-form"))

    def test_double_post_one_message(self):
        self.client.force_login(self.w.ax)
        token = str(uuid.uuid4())
        before = Message.objects.filter(dialog=self.ax_dialog).count()
        self.assertEqual(
            self.client.post("/chat/", {"text": "Привет", "client_token": token}).status_code,
            302,
        )
        self.assertEqual(
            self.client.post("/chat/", {"text": "Привет", "client_token": token}).status_code,
            302,
        )
        self.assertEqual(Message.objects.filter(dialog=self.ax_dialog).count(), before + 1)

    def test_post_invalid_shows_error(self):
        self.client.force_login(self.w.ax)
        before = Message.objects.count()
        response = self.client.post("/chat/", {"text": "   "})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Сообщение пустое.", response.content.decode())
        self.assertEqual(Message.objects.count(), before)

    def test_post_rate_limited_shows_error(self):
        self.client.force_login(self.w.ax)
        for _ in range(RATE_LIMIT_MESSAGES):
            self.client.post("/chat/", {"text": "сообщение"})
        response = self.client.post("/chat/", {"text": "лишнее"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Подождите немного", response.content.decode())

    def test_open_marks_student_read(self):
        dialog = self.ax_dialog
        add_message(dialog, self.w.ax, AuthorRole.STUDENT)
        reply = add_message(dialog, self.w.sx, AuthorRole.STAFF)
        self.assertEqual(dialog.student_read_id, 0)
        self.client.force_login(self.w.ax)
        self.client.get("/chat/")
        dialog.refresh_from_db()
        self.assertEqual(dialog.student_read_id, reply.pk)
        self.assertEqual(dialog.staff_read_id, 0)

    def test_staff_open_marks_read_for_all_staff(self):
        dialog = self.ax_dialog
        msg = add_message(dialog, self.w.ax, AuthorRole.STUDENT)
        self.assertEqual(dialog.staff_read_id, 0)
        self.client.force_login(self.w.sx)
        self.client.get(f"/staff/chats/{dialog.public_id}/")
        dialog.refresh_from_db()
        self.assertEqual(dialog.staff_read_id, msg.pk)
        self.assertEqual(dialog.student_read_id, 0)

    def test_staff_dialog_summary_link(self):
        self.client.force_login(self.w.sx)
        content = self.client.get(f"/staff/chats/{self.ax_uuid}/").content.decode()
        self.assertIn(f'href="/staff/students/{self.w.ax_profile.pk}/"', content)

    def test_staff_list_items(self):
        dialog = self.ax_dialog
        existing = dialog.messages.order_by("id").first()
        dialog.staff_read_id = existing.pk
        dialog.save(update_fields=["staff_read_id"])
        add_message(dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(dialog, self.w.ax, AuthorRole.STUDENT)
        self.client.force_login(self.w.sx)
        content = self.client.get("/staff/chats/").content.decode()
        self.assertIn(self.w.ax_profile.full_name, content)
        self.assertIn(self.w.ax_profile.group.name, content)
        self.assertIn("<strong>новых: 2</strong>", content)

    def test_no_store_on_all_chat_views(self):
        self.client.force_login(self.w.ax)
        urls = [
            "/chat/",
            "/chat/updates/?after=0",
        ]
        for url in urls:
            self.assertIn("no-store", self.client.get(url)["Cache-Control"])
        self.client.force_login(self.w.sx)
        urls = [
            "/staff/chats/",
            f"/staff/chats/{self.ax_uuid}/",
            f"/staff/chats/{self.ax_uuid}/updates/?after=0",
        ]
        for url in urls:
            self.assertIn("no-store", self.client.get(url)["Cache-Control"])


class UpdatesViewTests(_ChatWorld):
    def test_student_204_without_dialog(self):
        self.client.force_login(self.w.cx)
        response = self.client.get("/chat/updates/?after=0")
        self.assertEqual(response.status_code, 204)

    def test_student_204_nothing_new(self):
        self.client.force_login(self.w.ax)
        last = Message.objects.filter(dialog=self.ax_dialog).latest("id")
        response = self.client.get(f"/chat/updates/?after={last.pk}")
        self.assertEqual(response.status_code, 204)

    def test_student_returns_only_newer_fragment(self):
        self.client.force_login(self.w.ax)
        a = add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT, text="новое")
        after = self.ax_dialog.messages.order_by("id").first().pk
        response = self.client.get(f"/chat/updates/?after={after}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Chat-Fragment"], "1")
        content = response.content.decode()
        self.assertIn(f'data-message-id="{a.pk}"', content)
        self.assertNotIn("<html", content)
        self.assertNotIn("<nav", content)

    def test_fragment_marks_read_up_to_last_returned(self):
        dialog = self.ax_dialog
        add_message(dialog, self.w.sx, AuthorRole.STAFF, text="первый")
        second = add_message(dialog, self.w.sx, AuthorRole.STAFF, text="второй")
        self.client.force_login(self.w.ax)
        self.client.get("/chat/updates/?after=0")
        dialog.refresh_from_db()
        self.assertEqual(dialog.student_read_id, second.pk)

    def test_bad_after_400(self):
        self.client.force_login(self.w.ax)
        for bad in ("", "abc", "-1", "1e3", "1234567890123456789"):
            self.assertEqual(self.client.get(f"/chat/updates/?after={bad}").status_code, 400)

    def test_fragment_limit_50(self):
        dialog = self.ax_dialog
        for _ in range(60):
            add_message(dialog, self.w.ax, AuthorRole.STUDENT, text="x")
        first = dialog.messages.order_by("id").first().pk
        self.client.force_login(self.w.ax)
        content = self.client.get(f"/chat/updates/?after={first}").content.decode()
        self.assertEqual(content.count('data-message-id="'), 50)

    def test_staff_fragment_scope(self):
        self.client.force_login(self.w.sy)
        self.assertEqual(
            self.client.get(f"/staff/chats/{self.ax_uuid}/updates/?after=0").status_code, 404
        )
        self.client.force_login(self.w.sx)
        self.assertEqual(
            self.client.get(f"/staff/chats/{self.ax_uuid}/updates/?after=0").status_code, 200
        )

    def test_fragment_escapes_text(self):
        dialog = self.ax_dialog
        add_message(dialog, self.w.ax, AuthorRole.STUDENT, text="<b>x</b>")
        self.client.force_login(self.w.ax)
        content = self.client.get("/chat/updates/?after=0").content.decode()
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", content)


class AdminTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.dialog = make_dialog(cls.w.ax_profile)

    def test_admin_list_and_change_view_ok(self):
        self.client.force_login(self.w.root)
        self.assertEqual(self.client.get(reverse("admin:chat_dialog_changelist")).status_code, 200)
        self.assertEqual(
            self.client.get(reverse("admin:chat_dialog_change", args=[self.dialog.pk])).status_code,
            200,
        )

    def test_admin_is_read_only(self):
        self.client.force_login(self.w.root)
        self.assertEqual(self.client.get(reverse("admin:chat_dialog_add")).status_code, 403)
        self.assertEqual(
            self.client.post(
                reverse("admin:chat_dialog_change", args=[self.dialog.pk]), {}
            ).status_code,
            403,
        )


class NavTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_student_chat_count(self):
        dialog = make_dialog(self.w.ax_profile)
        add_message(dialog, self.w.sx, AuthorRole.STAFF)
        self.client.force_login(self.w.ax)
        content = self.client.get("/profile/").content.decode()
        self.assertEqual(content.count(">Чат (1)</a>"), 2)

    def test_student_chat_without_count(self):
        self.client.force_login(self.w.ax)
        content = self.client.get("/profile/").content.decode()
        self.assertEqual(content.count(">Чат</a>"), 2)

    def test_staff_nav_has_chats(self):
        self.client.force_login(self.w.sx)
        content = self.client.get("/profile/").content.decode()
        self.assertIn('href="/staff/chats/"', content)

    def test_badge_includes_chat_reply(self):
        dialog = make_dialog(self.w.ax_profile)
        add_message(dialog, self.w.sx, AuthorRole.STAFF)
        self.client.force_login(self.w.ax)
        content = self.client.get("/profile/").content.decode()
        self.assertIn(
            '<a class="site-menu-badge" href="/notifications/">Уведомления (1)</a>', content
        )


class QueryCountTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.dialog = make_dialog(cls.w.ax_profile)

    def test_student_page_constant(self):
        self.client.force_login(self.w.ax)
        add_message(self.dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(self.dialog, self.w.sx, AuthorRole.STAFF)
        small = _query_count(lambda: self.client.get("/chat/"))
        for _ in range(28):
            add_message(self.dialog, self.w.ax, AuthorRole.STUDENT)
        large = _query_count(lambda: self.client.get("/chat/"))
        self.assertEqual(small, large)
        self.assertLessEqual(small, 14)

    def test_staff_list_constant(self):
        self.client.force_login(self.w.sx)
        add_message(self.dialog, self.w.ax, AuthorRole.STUDENT)
        one = _query_count(lambda: self.client.get("/staff/chats/"))
        for i in range(5):
            student = make_student(f"extra{i}", self.w.gx1, f"REC-X-{i}")
            d = make_dialog(student.student_profile)
            add_message(d, student, AuthorRole.STUDENT)
        six = _query_count(lambda: self.client.get("/staff/chats/"))
        self.assertEqual(one, six)
        self.assertLessEqual(one, 6)

    def test_staff_dialog_constant(self):
        self.client.force_login(self.w.sx)
        add_message(self.dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(self.dialog, self.w.sx, AuthorRole.STAFF)
        small = _query_count(lambda: self.client.get(f"/staff/chats/{self.dialog.public_id}/"))
        for _ in range(28):
            add_message(self.dialog, self.w.ax, AuthorRole.STUDENT)
        large = _query_count(lambda: self.client.get(f"/staff/chats/{self.dialog.public_id}/"))
        self.assertEqual(small, large)
        self.assertLessEqual(small, 10)

    def test_fragment_constant(self):
        self.client.force_login(self.w.ax)
        base = add_message(self.dialog, self.w.ax, AuthorRole.STUDENT)
        add_message(self.dialog, self.w.sx, AuthorRole.STAFF)
        after = base.pk
        one = _query_count(lambda: self.client.get(f"/chat/updates/?after={after}"))
        for _ in range(9):
            add_message(self.dialog, self.w.sx, AuthorRole.STAFF)
        ten = _query_count(lambda: self.client.get(f"/chat/updates/?after={after}"))
        self.assertEqual(one, ten)
        self.assertLessEqual(one, 8)

    def test_header_student_four_queries(self):
        user = User.objects.get(pk=self.w.ax.pk)
        with self.assertNumQueries(4):
            badge_for_user(user)
            student_unread_count(user)

    def test_header_staff_no_chat_query(self):
        user = User.objects.get(pk=self.w.sx.pk)
        with self.assertNumQueries(0):
            student_unread_count(user)
