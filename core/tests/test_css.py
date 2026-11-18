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


BASE_CSS = Path(settings.BASE_DIR) / "static/css/base.css"
WIDE_MEDIA = "@media (min-width: 48rem)"


def _wide_blocks(css: str) -> list[str]:
    """Bodies of every `@media (min-width: 48rem) { ... }` block (brace matching)."""
    blocks = []
    start = css.find(WIDE_MEDIA)
    while start != -1:
        open_brace = css.index("{", start)
        depth = 0
        for i in range(open_brace, len(css)):
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(css[open_brace + 1 : i])
                    break
        start = css.find(WIDE_MEDIA, i)
    return blocks


def _outside_media(css: str) -> str:
    """The stylesheet with every @media block removed."""
    out = []
    i = 0
    while True:
        start = css.find("@media", i)
        if start == -1:
            out.append(css[i:])
            return "".join(out)
        out.append(css[i:start])
        depth = 0
        for j in range(css.index("{", start), len(css)):
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
                if depth == 0:
                    i = j + 1
                    break


def _rule(css: str, selector: str) -> str:
    """Joined bodies of the rules whose selector list contains `selector`."""
    bodies = []
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if selector in [part.strip() for part in sel.split(",")]:
            bodies.append(body)
    return "\n".join(bodies)


class MapLayoutCssTests(SimpleTestCase):
    """Wide map layout (TASK-013-FIX2)."""

    def setUp(self):
        self.css = BASE_CSS.read_text()

    def test_wide_two_columns(self):
        layouts = [_rule(block, ".map-layout") for block in _wide_blocks(self.css)]
        layout = next(body for body in layouts if "display: grid" in body)
        self.assertIn('"plan floors"', layout)
        self.assertIn('"plan side"', layout)
        self.assertIn("minmax(14rem, 1fr)", layout)
        plans = "\n".join(_rule(block, ".map-plan") for block in _wide_blocks(self.css))
        self.assertIn("position: sticky", plans)

    def test_plan_width_from_viewport(self):
        widths = "\n".join(_rule(block, ".map-plan .map-svg") for block in _wide_blocks(self.css))
        self.assertIn("width: clamp(20rem, calc((100vh - 13rem) * 0.6173), 32rem)", widths)

    def test_mobile_svg_rule_unchanged(self):
        outside = _outside_media(self.css)
        svg = _rule(outside, ".map-svg")
        self.assertIn("width: 100%", svg)
        self.assertIn("height: auto", svg)
        self.assertEqual(_rule(outside, ".map-layout"), "")

    def test_no_zoom_blocking(self):
        for path in sorted((Path(settings.BASE_DIR) / "static/css").glob("*.css")):
            with self.subTest(file=path.name):
                self.assertNotIn("touch-action: none", path.read_text())
        base = (Path(settings.BASE_DIR) / "templates/base.html").read_text()
        self.assertIn('content="width=device-width, initial-scale=1"', base)
        self.assertNotIn("maximum-scale", base)
        self.assertNotIn("user-scalable", base)
