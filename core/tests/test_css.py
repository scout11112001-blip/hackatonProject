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

    def test_map_highlight_rule(self):
        base_css = (Path(settings.BASE_DIR) / "static/css/base.css").read_text()
        tokens = (Path(settings.BASE_DIR) / "static/css/tokens.css").read_text()
        self.assertIn(".map-current .map-room-label", base_css)
        self.assertIn("var(--color-map-highlight)", base_css)
        self.assertIn("--color-map-highlight", tokens)

    def test_compact_nav_rules(self):
        base_css = (Path(settings.BASE_DIR) / "static/css/base.css").read_text()
        self.assertRegex(base_css, r"\.site-nav--wide\s*\{\s*display:\s*none;")
        self.assertRegex(
            base_css,
            r"@media \(min-width: 48rem\)\s*\{\s*\.site-nav--wide\s*\{\s*display:\s*block;\s*\}"
            r"\s*\.site-nav-compact\s*\{\s*display:\s*none;",
        )

    def test_chat_alignment_rules(self):
        base_css = (Path(settings.BASE_DIR) / "static/css/base.css").read_text()
        self.assertRegex(base_css, r"\.chat-message--own\s*\{\s*margin-left:")
        self.assertRegex(base_css, r"\.chat-message--other\s*\{\s*margin-right:")
        self.assertNotIn(".chat-message--student {", base_css)
        self.assertNotIn(".chat-message--staff {", base_css)
