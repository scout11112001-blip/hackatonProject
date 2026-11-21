"""Design system rules of the "night pixel" theme (TASK-012)."""

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

BASE = Path(settings.BASE_DIR)
CSS = BASE / "static/css"

REQUIRED_TOKENS = [
    "color-bg",
    "color-sky-1",
    "color-sky-2",
    "color-sky-3",
    "color-sky-4",
    "color-panel",
    "color-frame",
    "color-frame-gap",
    "color-text",
    "color-muted",
    "color-heading",
    "color-link",
    "color-accent",
    "color-border",
    "color-warn",
    "color-warn-text",
    "color-changed",
    "color-orange",
    "color-orange-light",
    "color-orange-dark",
    "color-orange-edge",
    "color-on-accent",
    "color-now-bg",
    "color-field-bg",
    "color-field-border",
    "color-focus",
    "color-star-yellow",
    "color-star-lilac",
    "color-map-highlight",
    "color-map-highlight-fill",
    "color-map-room-fill",
    # TASK-013: final map look and scrollbar tokens (D5).
    "color-map-highlight-text",
    "color-map-corridor-fill",
    "color-map-room-stroke",
    "color-map-landmark",
    "color-map-service",
    "color-map-hatch",
    "color-map-label-halo",
    "color-scroll-thumb",
    "color-scroll-thumb-hover",
    "font-body",
    "font-pixel",
    "font-heading",
    "font-size-title",
    "font-size-h1",
    "font-size-h2",
    "font-size-button",
    "font-size-tag",
    "frame-width",
]

TEXT_SELECTORS = {"body", "p", "li", "input", "select", "textarea", "table", "h3"}


def _read(relative: str) -> str:
    return (BASE / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((BASE / relative).read_bytes()).hexdigest()


def _rules(css: str) -> list[tuple[str, str]]:
    """Return (selector list, declarations) pairs; @media wrappers are flattened."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@media[^{]*\{", "", css)
    return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)]


def _rule_bodies(css: str, selector: str) -> str:
    return "\n".join(body for sel, body in _rules(css) if selector in sel.split(","))


def _project_templates() -> list[Path]:
    roots = [BASE / "templates"] + [
        path
        for path in BASE.glob("*/templates")
        if path.parent.name not in {".venv", "docs", "staticfiles"}
    ]
    return sorted(p for root in roots for p in root.rglob("*.html"))


class TokenTests(SimpleTestCase):
    def test_required_tokens(self):
        tokens = _read("static/css/tokens.css")
        for name in REQUIRED_TOKENS:
            with self.subTest(token=name):
                self.assertIn(f"--{name}:", tokens)
        for name, value in {
            "color-warn-text": "#ff8a95",
            "color-field-border": "#a58cf0",
            "color-on-accent": "#2b1300",
            "color-text": "#f3ecff",
        }.items():
            with self.subTest(token=name):
                self.assertRegex(tokens, rf"--{name}:\s*{value};")

    def test_no_colour_literals_outside_tokens(self):
        pattern = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|rgba|hsl|hsla)\(")
        for name in ("base.css", "theme.css"):
            with self.subTest(file=name):
                self.assertIsNone(pattern.search((CSS / name).read_text(encoding="utf-8")))


class FontTests(SimpleTestCase):
    def test_font_files_unchanged(self):
        self.assertEqual(
            _sha256("static/fonts/PressStart2P-Regular.ttf"),
            "034c77f1f05ec89421e4a63f0e3a4ca1ecf852cc6d2bf611f126f275728e017d",
        )
        self.assertEqual(
            _sha256("static/fonts/OFL.txt"),
            "705960c3281a5765ecc0b59bd4ed7ca59eed165748076bc2fc3e8fdbfeb944b0",
        )

    def test_font_found_by_staticfiles(self):
        self.assertIsNotNone(finders.find("fonts/PressStart2P-Regular.ttf"))
        self.assertIsNotNone(finders.find("fonts/OFL.txt"))
        self.assertEqual(
            sorted(os.listdir(BASE / "static/fonts")), ["OFL.txt", "PressStart2P-Regular.ttf"]
        )

    def test_font_face_rule(self):
        theme = _read("static/css/theme.css")
        match = re.search(
            r'@font-face\s*\{[^}]*font-family:\s*"Press Start 2P"[^}]*'
            r'url\("\.\./fonts/PressStart2P-Regular\.ttf"\)[^}]*\}',
            theme,
        )
        self.assertIsNotNone(match)
        self.assertIn("font-display: swap", match.group(0))
        self.assertRegex(_read("static/css/tokens.css"), r'--font-pixel:\s*"Press Start 2P"')

    def test_manifest_rewrites_font_url(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        storages = {
            **settings.STORAGES,
            "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
        }
        with override_settings(STATIC_ROOT=tmp, STORAGES=storages):
            call_command("collectstatic", interactive=False, verbosity=0)
        manifest = json.loads((Path(tmp) / "staticfiles.json").read_text())["paths"]
        theme = (Path(tmp) / manifest["css/theme.css"]).read_text(encoding="utf-8")
        font = Path(manifest["fonts/PressStart2P-Regular.ttf"]).name
        self.assertNotEqual(font, "PressStart2P-Regular.ttf")
        self.assertIn(f'url("../fonts/{font}")', theme)


class ExternalResourceTests(SimpleTestCase):
    def test_css_has_no_external_urls(self):
        for path in sorted(CSS.glob("*.css")):
            css = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                self.assertNotIn("@import", css)
                self.assertNotIn("https://", css)
                self.assertNotIn("http://", css)
                # TASK-013: fragment URLs (the inline SVG hatch pattern) are allowed (D6).
                for match in re.finditer(r"url\(", css):
                    self.assertRegex(css[match.start() :], r'^url\("?(\.\./|#)')

    def test_templates_have_no_external_urls(self):
        templates = _project_templates()
        self.assertGreater(len(templates), 30)
        for path in templates:
            text = path.read_text(encoding="utf-8")
            with self.subTest(template=str(path.relative_to(BASE))):
                self.assertNotIn("https://", text)
                self.assertNotIn("http://", text.replace("http://www.w3.org/2000/svg", ""))
                self.assertNotIn("fonts.googleapis", text)
                self.assertNotIn("fonts.gstatic", text)

    def test_scripts_only_where_expected(self):
        with_script = {
            str(path.relative_to(BASE))
            for path in _project_templates()
            if "<script" in path.read_text(encoding="utf-8")
        }
        self.assertEqual(
            with_script,
            {
                "chat/templates/chat/student.html",
                "chat/templates/chat/staff_dialog.html",
                "accounts/templates/accounts/login.html",  # TASK-017: password toggle
            },
        )
        self.assertEqual(sorted(os.listdir(BASE / "static/js")), ["chat.js", "password-toggle.js"])

    def test_no_admin_templates(self):
        self.assertFalse((BASE / "templates/admin").exists())


class LogoTests(SimpleTestCase):
    def test_favicon_file(self):
        svg = _read("static/img/favicon.svg")
        self.assertIn("<svg", svg)
        self.assertIn('shape-rendering="crispEdges"', svg)
        self.assertIn("<rect", svg)
        for forbidden in ("<script", "href=", "<image"):
            self.assertNotIn(forbidden, svg)

    def test_icon_includes(self):
        for name in ("icon_cap.html", "icon_bell.html"):
            text = _read(f"templates/includes/{name}")
            with self.subTest(icon=name):
                self.assertEqual(text.count("<svg"), 1)
                self.assertIn('aria-hidden="true"', text)
                self.assertIn('focusable="false"', text)
                self.assertIn('shape-rendering="crispEdges"', text)
                self.assertIn('fill="currentColor"', text)
                self.assertNotIn("xmlns", text)


class BaseTemplateLogoTests(TestCase):
    def test_base_links_favicon(self):
        content = self.client.get("/login/").content.decode()
        self.assertIn(
            '<link rel="icon" href="/static/img/favicon.svg" type="image/svg+xml">', content
        )
        self.assertIn('class="site-brand"', content)
        self.assertIn('<span class="site-title-line">Цифровой</span>', content)


class ThemeRuleTests(SimpleTestCase):
    def test_focus_visible(self):
        rules = _rules(_read("static/css/theme.css"))
        self.assertTrue(
            any(
                ":focus-visible" in sel and "outline" in body and "var(--color-focus)" in body
                for sel, body in rules
            )
        )

    def test_reduced_motion_if_motion(self):
        for path in sorted(CSS.glob("*.css")):
            css = path.read_text(encoding="utf-8")
            if "transition" in css or "animation" in css:
                with self.subTest(file=path.name):
                    self.assertIn("prefers-reduced-motion", css)

    def test_card_row_ellipsis(self):
        base = _read("static/css/base.css")
        title = _rule_bodies(base, ".card-row-title")
        for decl in ("white-space: nowrap", "overflow: hidden", "text-overflow: ellipsis"):
            self.assertIn(decl, title)
        self.assertIn("min-width: 0", title)
        label = _rule_bodies(base, ".card-row-label")
        self.assertIn("white-space: nowrap", label)
        self.assertTrue("flex: none" in label or "flex-shrink: 0" in label)
        self.assertIn("display: flex", _rule_bodies(base, ".card-row"))

    def test_home_actions_grid(self):
        base = _read("static/css/base.css")
        self.assertIn("grid-template-columns: 1fr 1fr", _rule_bodies(base, ".home-actions--two"))

    def test_map_highlight_not_hue_only(self):
        rules = _rules(_read("static/css/theme.css"))
        self.assertTrue(
            any(
                ".map-current" in sel
                and "stroke-width" in body
                and "var(--color-map-highlight)" in body
                for sel, body in rules
            )
        )

    def test_map_highlight_final(self):
        rules = _rules(_read("static/css/theme.css"))
        found = False
        for sel, body in rules:
            parts = {s.strip() for s in sel.split(",")}
            if parts & {".map-current rect", ".map-current polygon"}:
                width = re.search(r"stroke-width:\s*(\d+)", body)
                if "fill: var(--color-map-highlight-fill)" in body and width:
                    found = int(width.group(1)) >= 4
        self.assertTrue(found)

    def test_map_kinds_distinct(self):
        theme = _read("static/css/theme.css")
        self.assertIn("var(--color-map-landmark)", _rule_bodies(theme, ".map-landmark rect"))
        service = _rule_bodies(theme, ".map-service rect")
        self.assertIn("url(#map-hatch)", service)
        self.assertIn("var(--color-map-service)", service)
        service_label = _rule_bodies(theme, ".map-service-label")
        landmark_label = _rule_bodies(theme, ".map-landmark-label")
        self.assertIn("paint-order: stroke", service_label)

        def fill(body):
            return re.search(r"(?<![-\w])fill:\s*([^;]+);", body).group(1)

        self.assertNotEqual(fill(service_label), fill(landmark_label))

    def test_file_input_full_width(self):
        base = _read("static/css/base.css")
        self.assertIn("width: 100%", _rule_bodies(base, '.form input[type="file"]'))

    def test_scrollbar_rules(self):
        theme = _read("static/css/theme.css")
        for needle in (
            "scrollbar-width: thin",
            "scrollbar-color: var(--color-scroll-thumb)",
            "::-webkit-scrollbar-thumb",
            "var(--color-scroll-thumb-hover)",
            "@media (hover: hover) and (pointer: fine)",
        ):
            self.assertIn(needle, theme)
        for path in sorted(CSS.glob("*.css")):
            css = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                self.assertNotIn("scrollbar-width: none", css)
                for sel, body in _rules(css):
                    if "scrollbar" in sel:
                        self.assertNotRegex(body, r"display:\s*none")
                        radius = re.search(r"border-radius:\s*([^;]+);", body)
                        if radius:
                            self.assertRegex(radius.group(1).strip(), r"^0(px)?$")

    def test_body_font_for_text(self):
        self.assertRegex(
            _read("static/css/tokens.css"),
            r'--font-body:\s*system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;',
        )
        pixel = re.compile(r"font-family:\s*var\(--font-(?:pixel|heading)\)")
        for sel, body in _rules(_read("static/css/theme.css")):
            compounds = {part.strip() for part in sel.split(",")}
            if compounds & TEXT_SELECTORS:
                with self.subTest(selector=sel):
                    self.assertIsNone(pixel.search(body))


class ReadmeTests(SimpleTestCase):
    def test_design_section(self):
        readme = _read("README.md")
        self.assertIn("## Design", readme)
        self.assertIn("Press Start 2P", readme)
        self.assertIn("SIL Open Font License", readme)
        self.assertIn("static/fonts/OFL.txt", readme)
        self.assertIn("The logo and the favicon are our own pixel drawing", readme)

    def test_map_section_current(self):
        readme = _read("README.md")
        start = readme.index("## Map\n")
        section = readme[start : readme.index("\n## ", start + 1)]
        for needle in ("Туалет М", "Туалет Ж", "Вход", "Every floor has two staircases"):
            self.assertIn(needle, section)
        self.assertNotIn("Склад", section)


SEPARATOR_TEMPLATES = (
    "petitions/templates/petitions/my_list.html",
    "petitions/templates/petitions/staff_queue.html",
    "petitions/templates/petitions/catalog.html",
    "petitions/templates/petitions/includes/history.html",
    "petitions/templates/petitions/includes/comments.html",
    "chat/templates/chat/staff_list.html",
    "chat/templates/chat/_message.html",
    "accounts/templates/accounts/student_list.html",
    "schedule/templates/schedule/staff_group_list.html",
    "notifications/templates/notifications/feed.html",
    "notifications/templates/notifications/staff_list.html",
    "academics/templates/academics/includes/discipline.html",
    "schedule/templates/schedule/includes/lesson_compact.html",
)


class SeparatorRuleTests(SimpleTestCase):
    """A "·" is always glued to the previous part with "&nbsp;" (TASK-014-FIX)."""

    def test_no_whitespace_before_separator(self):
        for relative in SEPARATOR_TEMPLATES:
            text = _read(relative)
            with self.subTest(template=relative):
                self.assertIsNone(re.search(r"\s·", text))
                if relative.endswith("catalog.html"):
                    # The catalog has no separators at all (AC4).
                    self.assertNotIn("·", text)
                else:
                    self.assertIn("&nbsp;·", text)
