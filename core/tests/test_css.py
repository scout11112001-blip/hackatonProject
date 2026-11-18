"""Tests for the layout (base) stylesheet."""

import re
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
        # TASK-013: the highlight colours moved to theme.css; the number uses the dark
        # "on accent" token on the orange fill (D5, D6).
        self.assertIn("--color-map-highlight:", tokens)
        self.assertRegex(tokens, r"--color-map-highlight-fill:\s*#ff9f2e;")
        self.assertRegex(tokens, r"--color-map-highlight-text:\s*#2b1300;")
        theme = (Path(settings.BASE_DIR) / "static/css/theme.css").read_text()
        label_rules = [
            body
            for css in (base_css, theme)
            for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
            if ".map-current .map-room-label" in sel
        ]
        self.assertTrue(any("var(--color-map-highlight-text)" in b for b in label_rules))

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
