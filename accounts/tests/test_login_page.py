"""TASK-017: show/hide password toggle on the login page."""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

BASE = Path(settings.BASE_DIR)


class LoginToggleMarkupTests(TestCase):
    def _content(self, **post):
        if post:
            return self.client.post(reverse("accounts:login"), post).content.decode()
        return self.client.get(reverse("accounts:login")).content.decode()

    def _button(self, content):
        match = re.search(r"<button [^>]*data-password-toggle[^>]*>", content)
        self.assertIsNotNone(match)
        return match.group(0)

    def test_toggle_button_attributes(self):
        button = self._button(self._content())
        for attr in (
            'type="button"',
            'class="password-toggle"',
            'aria-controls="id_password"',
            'aria-pressed="false"',
            'aria-label="Показать пароль"',
            " hidden",
        ):
            self.assertIn(attr, button)

    def test_two_pixel_icons(self):
        content = self._content()
        start = content.index("data-password-toggle")
        end = content.index("</button>", start)
        inner = content[start:end]
        self.assertEqual(inner.count("<svg"), 2)
        self.assertIn('class="icon-eye"', inner)
        self.assertIn('class="icon-eye-off"', inner)
        self.assertEqual(inner.count('shape-rendering="crispEdges"'), 2)
        self.assertEqual(inner.count('aria-hidden="true"'), 2)
        self.assertEqual(inner.count('focusable="false"'), 2)
        self.assertNotIn("<path", inner)

    def test_script_external_and_deferred(self):
        content = self._content()
        self.assertIn('<script src="/static/js/password-toggle.js" defer></script>', content)
        self.assertNotIn("<script>", content)

    def test_fields_keep_autocomplete(self):
        content = self._content()
        self.assertRegex(content, r'<input type="text" name="username"[^>]*autocomplete="username"')
        self.assertRegex(
            content, r'<input type="password" name="password"[^>]*autocomplete="current-password"'
        )
        self.assertEqual(content.count('name="password"'), 1)
        self.assertIn('<label for="id_password">', content)
        self.assertIn('<label for="id_username">', content)

    def test_errors_still_shown(self):
        content = self._content(username="nobody", password="")
        self.assertIn('id="id_password_error"', content)
        self.assertIn('aria-describedby="id_password_error"', content)
        content = self._content(username="nobody", password="wrong")
        self.assertIn('class="errorlist nonfield"', content)
        self.assertIn("data-password-toggle", content)


class LoginToggleStaticTests(SimpleTestCase):
    def test_script(self):
        js = (BASE / "static/js/password-toggle.js").read_text(encoding="utf-8")
        for fragment in (
            "[data-password-toggle]",
            'getAttribute("aria-controls")',
            'setAttribute("aria-pressed"',
            '"text" : "password"',
            '"submit"',
            "button.hidden = false",
        ):
            self.assertIn(fragment, js)
        for forbidden in ("innerHTML", "eval(", "aria-label", "fetch(", "localStorage"):
            self.assertNotIn(forbidden, js)

    def test_css(self):
        base = (BASE / "static/css/base.css").read_text(encoding="utf-8")
        self.assertRegex(base, r"\.password-toggle\[hidden\]\s*\{\s*display:\s*none;")
        self.assertRegex(base, r"\.password-toggle\s*\{[^}]*min-width:\s*2\.75rem")
        self.assertRegex(base, r"\.password-toggle\s*\{[^}]*min-height:\s*2\.75rem")
        self.assertRegex(
            base,
            r'\.password-toggle\[aria-pressed="true"\]\s*\.icon-eye-off\s*\{\s*display:\s*block',
        )

    def test_icons(self):
        for name in ("icon_eye.html", "icon_eye_off.html"):
            svg = (BASE / "templates/includes" / name).read_text(encoding="utf-8")
            self.assertIn('shape-rendering="crispEdges"', svg)
            self.assertIn('fill="currentColor"', svg)
            self.assertIn("<rect", svg)
            for forbidden in ("style=", "<path", "<script", "href="):
                self.assertNotIn(forbidden, svg)
