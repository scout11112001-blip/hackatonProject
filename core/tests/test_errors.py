"""Themed error pages (TASK-012, AC13)."""

from pathlib import Path

from django.conf import settings
from django.test import RequestFactory, TestCase
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
