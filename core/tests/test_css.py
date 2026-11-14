"""Tests for the layout (base) stylesheet."""

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class BaseCssTests(SimpleTestCase):
    def test_form_controls_capped(self):
        base_css = (Path(settings.BASE_DIR) / "static/css/base.css").read_text()
        pattern = r"input,\s*select,\s*textarea,\s*button\s*\{[^}]*max-width:\s*100%"
        self.assertRegex(base_css, pattern)
        tokens = (Path(settings.BASE_DIR) / "static/css/tokens.css").read_text()
        theme = (Path(settings.BASE_DIR) / "static/css/theme.css").read_text()
        self.assertNotIn("max-width: 100%", tokens)
        self.assertNotIn("max-width: 100%", theme)
