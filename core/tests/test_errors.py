"""Themed error pages (TASK-012, AC13)."""

from pathlib import Path

from django.conf import settings
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.views.defaults import server_error

from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student


class ErrorPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.student = make_student("stu", cls.group, "REC-1")
        cls.staff = make_staff("stf", cls.faculty)

    def test_404_anonymous(self):
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        content = response.content.decode()
        self.assertIn("<h1>Страница не найдена</h1>", content)
        self.assertIn('<a class="btn" href="/">На главную</a>', content)

    def test_404_student(self):
        self.client.force_login(self.student)
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        content = response.content.decode()
        self.assertIn("<h1>Страница не найдена</h1>", content)
        self.assertIn('class="btn site-notif"', content)

    def test_403_student_on_staff_page(self):
        self.client.force_login(self.student)
        response = self.client.get("/staff/requests/")
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")
        self.assertIn("<h1>Доступ запрещён</h1>", response.content.decode())

    def test_403_staff_on_student_page(self):
        self.client.force_login(self.staff)
        response = self.client.get("/requests/")
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")

    def test_500_standalone(self):
        with self.assertNumQueries(0):
            response = server_error(RequestFactory().get("/"))
        self.assertEqual(response.status_code, 500)
        content = response.content.decode()
        self.assertIn("<h1>Ошибка сервера</h1>", content)
        self.assertIn('href="/static/css/theme.css"', content)
        self.assertIn('rel="icon"', content)
        self.assertNotIn("{%", content)
        template = (Path(settings.BASE_DIR) / "templates/500.html").read_text()
        self.assertNotIn("{% extends", template)


class CsrfFailurePageTests(TestCase):
    """TASK-016-FIX: a themed CSRF failure page instead of Django's page with inline CSS."""

    def test_csrf_failure_uses_project_template(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("accounts:login"), {"username": "a", "password": "b"})
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403_csrf.html")
        self.assertTemplateUsed(response, "base.html")
        content = response.content.decode()
        self.assertIn("<h1>Форма устарела</h1>", content)
        self.assertIn("Вернитесь назад, обновите страницу и отправьте форму ещё раз.", content)
        self.assertIn('href="/static/css/theme.css"', content)
        self.assertNotIn("<style", content)
        self.assertNotIn("CSRF", content)
        self.assertIn("Content-Security-Policy", response)

    def test_template_has_no_inline_code(self):
        text = (Path(settings.BASE_DIR) / "templates" / "403_csrf.html").read_text(encoding="utf-8")
        for forbidden in ("<style", "style=", "<script", "javascript:"):
            self.assertNotIn(forbidden, text)
        self.assertNotRegex(text, r"\son[a-z]+\s*=")
