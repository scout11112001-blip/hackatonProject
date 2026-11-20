"""TASK-016: Content-Security-Policy and no-store for signed-in users (PT1-F3, PT1-F5)."""

import re
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from core.middleware import (
    CONTENT_SECURITY_POLICY,
    ContentSecurityPolicyMiddleware,
    PrivateCacheMiddleware,
)

EXPECTED_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
    "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)


class ContentSecurityPolicyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fac = make_faculty("FX")
        group = make_group(fac, "GX")
        cls.student = make_student("csp_student", group, "SA")
        cls.staff = make_staff("csp_staff", fac)
        cls.admin = User.objects.create_superuser("csp_admin", password="Admin-Pass-2026!")

    def test_policy_value(self):
        self.assertEqual(CONTENT_SECURITY_POLICY, EXPECTED_CSP)

    def test_anonymous_login_page(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response["Content-Security-Policy"], EXPECTED_CSP)

    def test_student_page(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Security-Policy"], EXPECTED_CSP)

    def test_staff_page(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("petitions:staff_queue"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Security-Policy"], EXPECTED_CSP)

    def test_admin_page_same_policy(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Security-Policy"], EXPECTED_CSP)

    def test_redirect_and_404(self):
        self.assertEqual(self.client.get("/grades/")["Content-Security-Policy"], EXPECTED_CSP)
        self.client.force_login(self.student)
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Security-Policy"], EXPECTED_CSP)

    @override_settings(DEBUG=True)
    def test_debug_error_pages_without_policy(self):
        self.client.force_login(self.student)
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Content-Security-Policy", response)

    def test_existing_header_kept(self):
        def view(request):
            response = HttpResponse("x")
            response["Content-Security-Policy"] = "default-src 'none'"
            return response

        response = ContentSecurityPolicyMiddleware(view)(RequestFactory().get("/x/"))
        self.assertEqual(response["Content-Security-Policy"], "default-src 'none'")


class TemplatesFitPolicyTests(SimpleTestCase):
    """The strict policy works only while templates stay free of inline code."""

    FORBIDDEN = (
        re.compile(r"<script(?![^>]*\ssrc=)[^>]*>", re.IGNORECASE),
        re.compile(r"<style", re.IGNORECASE),
        re.compile(r"\sstyle\s*=", re.IGNORECASE),
        re.compile(r"\son[a-z]+\s*=", re.IGNORECASE),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", re.IGNORECASE),
        re.compile(r"data:image", re.IGNORECASE),
    )

    def test_no_inline_code_in_templates(self):
        base = Path(settings.BASE_DIR)
        paths = sorted(base.glob("templates/**/*.html")) + sorted(
            base.glob("*/templates/**/*.html")
        )
        self.assertGreater(len(paths), 30)
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for pattern in self.FORBIDDEN:
                self.assertIsNone(pattern.search(text), f"{path.relative_to(base)}: {pattern}")


class PrivateCacheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fac = make_faculty("FX")
        group = make_group(fac, "GX")
        cls.student = make_student("cache_student", group, "SA")
        cls.staff = make_staff("cache_staff", fac)

    def _assert_no_store(self, response):
        cache_control = response["Cache-Control"]
        self.assertIn("no-store", cache_control)
        self.assertIn("private", cache_control)

    def test_student_pages_no_store(self):
        self.client.force_login(self.student)
        for name in ("accounts:profile", "academics:my_grades", "schedule:week"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self._assert_no_store(response)

    def test_staff_page_no_store(self):
        self.client.force_login(self.staff)
        self._assert_no_store(self.client.get(reverse("petitions:staff_queue")))

    def test_anonymous_unchanged(self):
        response = self.client.get("/grades/")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("Cache-Control", response)

    def test_stale_session_cookie_unchanged(self):
        self.client.cookies[settings.SESSION_COOKIE_NAME] = "no-such-session"
        response = self.client.get("/grades/")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("Cache-Control", response)

    def test_no_session_access_without_cookie(self):
        request = RequestFactory().get("/x/")
        response = PrivateCacheMiddleware(lambda r: HttpResponse("x"))(request)
        self.assertNotIn("Cache-Control", response)
        self.assertFalse(hasattr(request, "user"))

    def test_session_length_unchanged(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 14 * 24 * 3600)
