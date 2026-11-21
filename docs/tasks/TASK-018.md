# TASK-018: scattered side stars on wide screens, "Чаты (n)" for staff

Author: Planner. Assignee: UI coder. Status: ready for implementation.
Base: HEAD 094dd55 (clean tree). Two Pentester threads work on copies and production; they do not touch the
working tree. Do not touch `plan.md`.

## 1. Goal

Two user requests (21.11).

1. On the desktop the side stars sit only at the window edges and read as two zig-zag "ladders"
   (`static/css/theme.css`: `body::before` / `body::after` put every side star into a 3–4 px column at
   `left: 4px` / `right: 5px`). Wide screens get stars scattered over the whole free side margins.
2. Staff see "Чаты" without a count. They get "Чаты (n)": unread student messages in the dialogs they can see.

### Acceptance criteria

| ID | Criterion |
|---|---|
| AC1 | From 64rem (1024 px) the side stars are scattered irregularly over both free side margins beside the content column (varied x and y; no column, row, straight line or ladder), same two token colours, 3 px square pixels, pure CSS (no markup, no JavaScript, no image, no inline style). |
| AC2 | The stars are never over the content column, the header or the footer (D13 of TASK-012 stays): the star layers stand beside `.site-main` only, below the content (`z-index: -1`), `pointer-events: none`, no horizontal scroll. |
| AC3 | Below 64rem nothing changes (the TASK-012 edge stars and header stars stay as they are; 360 px is identical). |
| AC4 | Staff (`role=staff`) see "Чаты (n)" in both menus (wide and compact), n = student messages with `id > dialog.staff_read_id` in the dialogs of active students of their faculty — the "new" rule of the staff chat list. Cap "99+", nothing at 0, computed on page load (no polling), one COUNT query, independent of the number of dialogs and messages. |
| AC5 | The read marker stays shared by the faculty's staff: when one staff member opens a dialog, the count drops for all of them. The student badge is unchanged; superusers and anonymous users get no badge. |
| AC6 | All verification commands pass; visual check reported (section 8). |

## 2. Out of scope

Polling or live update of the staff badge; the staff chat list page; the notifications badge (students only);
the header stars (`.site-header::after`, hidden from 48rem); stars below the footer on short pages (see D3);
any migration; `README.md` (its theme section says "pixel stars" without positions — still true).

## 3. Design decisions

- **D1. Star layers are `.site-main::before` (left margin) and `.site-main::after` (right margin).** `.site-main`
  is the content column (`max-width: var(--content-max-width)` = 60rem, `position: relative`, `z-index: 1`), so a
  layer with `top: 0; bottom: 0` spans exactly the content height and is never beside the header or the footer
  (the footer text starts 24 px from the left window edge and runs ~760 px, so it lies inside the left margin
  at every wide width; anchoring to `body` would put stars over it on short pages). `.site-main` has no
  other pseudo-elements. `z-index: -1` paints the layer above the page background and below everything inside
  the column.
- **D2. Width `calc(50vw - 50% - 1rem)`, placed at `right: 100%` / `left: 100%`.** `50%` is half the column
  width, so `50vw - 50%` is the margin. `100vw` includes a classic (non-overlay) scrollbar; the `1rem` kept free at
  the window edge keeps the right layer inside the viewport for scrollbars up to 32 px (otherwise the
  absolutely positioned layer would add a horizontal scrollbar). Checked: `scrollWidth == clientWidth` at 1024,
  1280, 1440 and 1920.
- **D3. A star is one background layer**: `linear-gradient(<colour> 0 3px, transparent 3px)` with
  `background-size: 3px 1600px` and `background-repeat: no-repeat repeat`, so the 3 × 3 px pixel repeats every
  1600 px down the page (long pages stay starry, the repeat is never visible inside one screen). `x` is a
  percentage of the margin width (the star spreads with the margin), `y` is px from the top of the column. The
  pixels are crisp at deviceScaleFactor 1 and 2 (checked with an 3× zoomed screenshot). On short pages (login:
  column 410 px high) there are stars only beside the column; the sky below the footer stays empty — the footer
  position is unknown to CSS, and stars there could cover the footer text.
- **D4. Breakpoints from the 60rem column.** From 64rem the margin layer is ≥ 1rem wide (16 px at 1024): group
  `a`, 8 stars per side per 1600 px. From 80rem (1280, layer ≥ 9rem): groups `a + b`, 16 stars. From 100rem
  (1600, layer ≥ 19rem): groups `a + b + c`, 26 stars. Groups are nested, so a wider screen only adds stars and
  the density stays even. The lists live in custom properties (`--stars-a-image`, `--stars-a-position`, …) on
  each layer; the 80rem and 100rem blocks only join them. At 1024 the margin is only 32 px, so the stars there
  still stand in a narrow band, but with irregular x over 16 px instead of the old 0–3 px.
- **D5. Positions were generated, then frozen.** Best-candidate (blue-noise) sampling with the rules of the
  scatter tests: two stars closer than 400 px vertically are ≥ 6 % of the margin apart (no column), no three
  neighbours in a 48 px band (no row), the middle of three neighbours is ≥ 10 % off the line through the outer two
  (no diagonal / ladder), every breakpoint covers x ≤ 10 % … ≥ 90 % and has no vertical gap over 400 px. Colours
  alternate in generation order (both colours in every group). The values are in F1; do not change them by hand
  without running `core/tests/test_stars.py`.
- **D6. Staff count as one query with joins.** `staff_unread_count` filters messages by
  `dialog__student__group__program__faculty__staff_members__user_id=user.pk` and
  `dialog__student__user__is_active=True` — the rule of `dialogs_visible_to` / `students_visible_to` for staff
  written as joins. Reusing `dialogs_visible_to(user)` would load the staff profile and its faculty first
  (3 queries on pages that do not use them, e.g. the map: `campusmap/tests/test_views.py::MapQueryTests::
  test_queries_constant` allows ≤ 4 and fails with 6). `StaffProfile.user` is one-to-one, so the join adds no
  duplicate rows; a staff user without a profile gets 0. `test_matches_visibility_rule` compares the result with
  the `dialogs_visible_to` count for four staff users (own faculty, colleague, other faculty, no profile) and an
  inactive student, so the two rules cannot drift apart silently.
- **D7. One tag for both roles.** `chat_unread_count(user)` returns the student count, the staff count or 0;
  `chat_unread_badge` keeps its cap/hiding logic and now calls it. `base.html` computes `chat_badge` for staff
  too (`{% elif user.is_deanery_staff %}`), the nav item shows it like the student item. Superusers have role
  `admin` → no query, no badge. The staff header with "Чаты (99+)" still fits on one line at 1024 px (checked).

## 4. Files and functions

Change: `static/css/theme.css`, `chat/selectors.py`, `chat/templatetags/chat_tags.py`, `templates/base.html`,
`templates/includes/site_nav_items.html`, `chat/tests/test_selectors.py`, `chat/tests/test_views.py`. Create:
`core/tests/test_stars.py`. Diffs are against HEAD 094dd55; edit by hand, no git commands.

### F1. `static/css/theme.css` (new block after the 48rem header-star block, nothing else changes)

````diff
--- a/static/css/theme.css
+++ b/static/css/theme.css
@@ -94,6 +94,179 @@
   }
 }
 
+/* Wide screens (TASK-018): the side stars are scattered over the free margins on both sides
+   of the content column. Each margin is a layer beside .site-main, so stars are never beside
+   the header or the footer. A star is a 3 px background tile: x in % of the margin width
+   (counted from the window edge), y in px from the top of the content column, repeated every
+   1600 px down the page. The 1rem kept free at the window edge keeps the layer inside the
+   viewport also with a classic scrollbar (100vw includes it). Breakpoints come from the
+   60rem content column: from 64rem the margin layer is at least 1rem wide (8 stars per side
+   in 1600 px), from 80rem at least 9rem (16 stars), from 100rem at least 19rem (26 stars).
+   The groups a, b and c are nested, so a wider screen only adds stars. */
+@media (min-width: 64rem) {
+  body::before,
+  body::after {
+    display: none;
+  }
+
+  .site-main::before,
+  .site-main::after {
+    --star-yellow: linear-gradient(var(--color-star-yellow) 0 3px, transparent 3px);
+    --star-lilac: linear-gradient(var(--color-star-lilac) 0 3px, transparent 3px);
+    content: "";
+    position: absolute;
+    top: 0;
+    bottom: 0;
+    width: calc(50vw - 50% - 1rem);
+    pointer-events: none;
+    z-index: -1;
+    background-image: var(--stars-a-image);
+    background-position: var(--stars-a-position);
+    background-size: 3px 1600px;
+    background-repeat: no-repeat repeat;
+  }
+
+  .site-main::before {
+    right: 100%;
+    --stars-a-image:
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-lilac),
+      var(--star-lilac),
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-yellow),
+      var(--star-yellow);
+    --stars-a-position:
+      94% 80px,
+      10% 118px,
+      87% 458px,
+      13% 572px,
+      76% 902px,
+      3% 1014px,
+      25% 1298px,
+      85% 1458px;
+    --stars-b-image:
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-lilac),
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-yellow),
+      var(--star-yellow),
+      var(--star-lilac);
+    --stars-b-position:
+      57% 224px,
+      26% 332px,
+      50% 562px,
+      96% 702px,
+      28% 738px,
+      69% 1092px,
+      91% 1272px,
+      32% 1544px;
+    --stars-c-image:
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-yellow),
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-lilac),
+      var(--star-lilac),
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-yellow);
+    --stars-c-position:
+      66% 344px,
+      34% 428px,
+      63% 780px,
+      37% 910px,
+      44% 1024px,
+      19% 1154px,
+      59% 1218px,
+      9% 1226px,
+      52% 1344px,
+      45% 1430px;
+  }
+
+  .site-main::after {
+    left: 100%;
+    --stars-a-image:
+      var(--star-yellow),
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-lilac),
+      var(--star-yellow),
+      var(--star-lilac);
+    --stars-a-position:
+      6% 182px,
+      82% 378px,
+      34% 518px,
+      25% 756px,
+      96% 1020px,
+      4% 1194px,
+      25% 1468px,
+      96% 1518px;
+    --stars-b-image:
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-lilac),
+      var(--star-lilac),
+      var(--star-yellow),
+      var(--star-yellow);
+    --stars-b-position:
+      38% 32px,
+      90% 80px,
+      59% 194px,
+      55% 668px,
+      88% 748px,
+      19% 976px,
+      69% 1136px,
+      75% 1284px;
+    --stars-c-image:
+      var(--star-lilac),
+      var(--star-yellow),
+      var(--star-yellow),
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-yellow),
+      var(--star-yellow),
+      var(--star-lilac),
+      var(--star-lilac),
+      var(--star-lilac);
+    --stars-c-position:
+      76% 272px,
+      26% 306px,
+      48% 402px,
+      96% 570px,
+      9% 638px,
+      78% 868px,
+      46% 894px,
+      31% 1090px,
+      10% 1318px,
+      50% 1394px;
+  }
+}
+
+@media (min-width: 80rem) {
+  .site-main::before,
+  .site-main::after {
+    background-image: var(--stars-a-image), var(--stars-b-image);
+    background-position: var(--stars-a-position), var(--stars-b-position);
+  }
+}
+
+@media (min-width: 100rem) {
+  .site-main::before,
+  .site-main::after {
+    background-image: var(--stars-a-image), var(--stars-b-image), var(--stars-c-image);
+    background-position: var(--stars-a-position), var(--stars-b-position), var(--stars-c-position);
+  }
+}
+
 /* Links and focus. */
 a {
   color: var(--color-link);
````

### F2. `chat/selectors.py`

````diff
--- a/chat/selectors.py
+++ b/chat/selectors.py
@@ -57,3 +57,33 @@
         author_role=AuthorRole.STAFF,
         id__gt=F("dialog__student_read_id"),
     ).count()
+
+
+def staff_unread_count(user: AbstractBaseUser | AnonymousUser) -> int:
+    """Unread student messages in the dialogs this staff member can see (TASK-018).
+
+    Same rule as the "new" count of ``staff_dialog_list``: student messages after the shared
+    read marker ``staff_read_id``. The dialog filter is the rule of ``dialogs_visible_to``
+    (active students of the staff member's faculty) written as joins, so the menu badge is one
+    COUNT query on every page; ``StaffUnreadCountTests.test_matches_visibility_rule`` keeps
+    the two in step.
+    """
+    if not user.is_authenticated or not user.is_active or user.role != User.Role.STAFF:
+        return 0
+    return Message.objects.filter(
+        dialog__student__group__program__faculty__staff_members__user_id=user.pk,
+        dialog__student__user__is_active=True,
+        author_role=AuthorRole.STUDENT,
+        id__gt=F("dialog__staff_read_id"),
+    ).count()
+
+
+def chat_unread_count(user: AbstractBaseUser | AnonymousUser) -> int:
+    """Count for the "Чат (n)" / "Чаты (n)" menu item; 0 for every other role."""
+    if not user.is_authenticated or not user.is_active:
+        return 0
+    if user.role == User.Role.STUDENT:
+        return student_unread_count(user)
+    if user.role == User.Role.STAFF:
+        return staff_unread_count(user)
+    return 0
````

### F3. `chat/templatetags/chat_tags.py`

````diff
--- a/chat/templatetags/chat_tags.py
+++ b/chat/templatetags/chat_tags.py
@@ -1,7 +1,7 @@
 from django import template
 
 from chat.constants import CHAT_BADGE_CAP
-from chat.selectors import student_unread_count
+from chat.selectors import chat_unread_count
 
 register = template.Library()
 
@@ -11,7 +11,7 @@
     request = context.get("request")
     if request is None:
         return ""
-    count = student_unread_count(request.user)
+    count = chat_unread_count(request.user)
     if count == 0:
         return ""
     if count > CHAT_BADGE_CAP:
````

### F4. Templates

````diff
--- a/templates/base.html
+++ b/templates/base.html
@@ -14,7 +14,7 @@
   <a class="skip-link" href="#main">Перейти к содержимому</a>
   <header class="site-header">
     <a class="site-brand" href="{% url 'core:home' %}">{% include "includes/icon_cap.html" %}<span class="site-title"><span class="site-title-line">Цифровой</span> <span class="site-title-line">деканат</span></span></a>
-    {% if user.is_student %}{% notifications_badge as badge %}{% chat_unread_badge as chat_badge %}{% endif %}
+    {% if user.is_student %}{% notifications_badge as badge %}{% chat_unread_badge as chat_badge %}{% elif user.is_deanery_staff %}{% chat_unread_badge as chat_badge %}{% endif %}
     <nav class="site-nav site-nav--wide" aria-label="Основная навигация">
       {% block nav %}{% if user.is_authenticated %}{% include "includes/site_nav_items.html" %}{% endif %}{% endblock %}
     </nav>
````

````diff
--- a/templates/includes/site_nav_items.html
+++ b/templates/includes/site_nav_items.html
@@ -10,7 +10,7 @@
   {% url 'schedule:staff_groups' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Расписание</a></li>
   {% url 'campusmap:map' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Карта</a></li>
   {% url 'petitions:staff_queue' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Документы</a></li>
-  {% url 'chat:staff_list' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Чаты</a></li>
+  {% url 'chat:staff_list' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Чаты{% if chat_badge %} ({{ chat_badge }}){% endif %}</a></li>
   {% url 'notifications:staff_announcements' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Объявления</a></li>
   {% endif %}
   {% if user.is_deanery_staff %}
````

### F5. Tests

`core/tests/test_stars.py` (new):

````python
"""Side stars on wide screens (TASK-018): CSS only, beside the content column, scattered."""

import re
from itertools import pairwise
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

BASE = Path(settings.BASE_DIR)
TILE = 1600
WIDE = ("(min-width: 64rem)", "(min-width: 80rem)", "(min-width: 100rem)")
GROUP_SIZES = {"a": 8, "b": 8, "c": 10}
TIERS = {"(min-width: 64rem)": "a", "(min-width: 80rem)": "ab", "(min-width: 100rem)": "abc"}
STAR_IMAGES = {"var(--star-yellow)", "var(--star-lilac)"}
SIDES = (".site-main::before", ".site-main::after")


def _css() -> str:
    text = (BASE / "static/css/theme.css").read_text(encoding="utf-8")
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def _media_blocks(css: str) -> tuple[list[tuple[str, str]], str]:
    """Return ([(condition, body)] of the top-level @media blocks, the CSS outside them)."""
    blocks, outside, i = [], [], 0
    while True:
        start = css.find("@media", i)
        if start == -1:
            outside.append(css[i:])
            return blocks, "".join(outside)
        outside.append(css[i:start])
        open_brace = css.index("{", start)
        depth = 0
        for j in range(open_brace, len(css)):
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
                if depth == 0:
                    break
        blocks.append((css[start + len("@media") : open_brace].strip(), css[open_brace + 1 : j]))
        i = j + 1


def _rules(css: str) -> list[tuple[list[str], str]]:
    return [
        ([part.strip() for part in sel.split(",")], body)
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
    ]


def _decl(body: str, name: str) -> str | None:
    match = re.search(rf"(?:^|[;{{\s]){re.escape(name)}\s*:\s*([^;]+);", body)
    return " ".join(match.group(1).split()) if match else None


def _block(condition: str) -> str:
    blocks, _ = _media_blocks(_css())
    bodies = [body for cond, body in blocks if cond == condition]
    if not bodies:
        raise AssertionError(f"no @media {condition} block")
    return "\n".join(bodies)


def _rule_in(css: str, selector: str, alone: bool = False) -> str:
    return "\n".join(
        body
        for selectors, body in _rules(css)
        if selector in selectors and (not alone or selectors == [selector])
    )


def _stars(side: str) -> dict[str, list[tuple[str, int, int]]]:
    body = _rule_in(_block(WIDE[0]), side, alone=True)
    groups = {}
    for group in GROUP_SIZES:
        images = _decl(body, f"--stars-{group}-image")
        positions = _decl(body, f"--stars-{group}-position")
        if images is None or positions is None:
            raise AssertionError(f"{side}: group {group} missing")
        image_list = [part.strip() for part in images.split(",")]
        position_list = [part.strip() for part in positions.split(",")]
        if len(image_list) != len(position_list):
            raise AssertionError(f"{side}: group {group} image/position counts differ")
        stars = []
        for image, position in zip(image_list, position_list, strict=True):
            match = re.fullmatch(r"(\d+)% (\d+)px", position)
            if not match:
                raise AssertionError(f"{side}: bad position {position!r}")
            stars.append((image, int(match.group(1)), int(match.group(2))))
        groups[group] = stars
    return groups


def _dy(a: int, b: int) -> int:
    d = abs(a - b)
    return min(d, TILE - d)


class WideStarsPlacementTests(SimpleTestCase):
    def test_narrow_screens_keep_edge_stars(self):
        blocks, outside = _media_blocks(_css())
        self.assertIn("left: 4px", _rule_in(outside, "body::before"))
        self.assertIn("box-shadow", _rule_in(outside, "body::before"))
        self.assertIn("right: 5px", _rule_in(outside, "body::after"))
        for side in SIDES:
            with self.subTest(side=side):
                self.assertEqual(_rule_in(outside, side), "")
                for condition, body in blocks:
                    if condition not in WIDE:
                        self.assertEqual(_rule_in(body, side), "", condition)

    def test_wide_screens_hide_edge_columns(self):
        block = _block(WIDE[0])
        for selector in ("body::before", "body::after"):
            with self.subTest(selector=selector):
                self.assertEqual(_decl(_rule_in(block, selector), "display"), "none")

    def test_layers_beside_content_column(self):
        block = _block(WIDE[0])
        shared = "\n".join(body for selectors, body in _rules(block) if selectors == list(SIDES))
        expected = {
            "content": '""',
            "position": "absolute",
            "top": "0",
            "bottom": "0",
            "width": "calc(50vw - 50% - 1rem)",
            "pointer-events": "none",
            "z-index": "-1",
            "background-size": "3px 1600px",
            "background-repeat": "no-repeat repeat",
        }
        for name, value in expected.items():
            with self.subTest(declaration=name):
                self.assertEqual(_decl(shared, name), value)
        self.assertEqual(_decl(_rule_in(block, SIDES[0], alone=True), "right"), "100%")
        self.assertEqual(_decl(_rule_in(block, SIDES[1], alone=True), "left"), "100%")

    def test_stars_are_token_coloured_gradients(self):
        shared = _rule_in(_block(WIDE[0]), SIDES[0])
        self.assertEqual(
            _decl(shared, "--star-yellow"),
            "linear-gradient(var(--color-star-yellow) 0 3px, transparent 3px)",
        )
        self.assertEqual(
            _decl(shared, "--star-lilac"),
            "linear-gradient(var(--color-star-lilac) 0 3px, transparent 3px)",
        )
        for condition in WIDE:
            with self.subTest(condition=condition):
                self.assertNotIn("url(", _block(condition))

    def test_breakpoints_add_groups(self):
        for condition, groups in TIERS.items():
            body = _rule_in(_block(condition), SIDES[0])
            with self.subTest(condition=condition):
                self.assertEqual(
                    _decl(body, "background-image"),
                    ", ".join(f"var(--stars-{g}-image)" for g in groups),
                )
                self.assertEqual(
                    _decl(body, "background-position"),
                    ", ".join(f"var(--stars-{g}-position)" for g in groups),
                )

    def test_no_star_markup_or_inline_style(self):
        base = (BASE / "templates/base.html").read_text(encoding="utf-8")
        self.assertNotRegex(base, r'class="[^"]*\bstar')
        self.assertNotIn("style=", base)


class WideStarsScatterTests(SimpleTestCase):
    """The stars of every breakpoint form no column, row or straight line (the old "ladder")."""

    def test_group_sizes_and_values(self):
        for side in SIDES:
            for group, stars in _stars(side).items():
                with self.subTest(side=side, group=group):
                    self.assertEqual(len(stars), GROUP_SIZES[group])
                    self.assertTrue({image for image, _, _ in stars} <= STAR_IMAGES)
                    self.assertEqual({image for image, _, _ in stars}, STAR_IMAGES)
                    for _, x, y in stars:
                        self.assertTrue(0 <= x <= 100 and 0 <= y < TILE, (x, y))

    def _tiers(self):
        for side in SIDES:
            groups = _stars(side)
            for condition, names in TIERS.items():
                yield side, condition, [(x, y) for n in names for _, x, y in groups[n]]

    def test_no_columns(self):
        # Two stars closer than 400 px vertically are at least 6 % of the margin apart.
        for side, condition, stars in self._tiers():
            with self.subTest(side=side, condition=condition):
                for i, a in enumerate(stars):
                    for b in stars[i + 1 :]:
                        if _dy(a[1], b[1]) < 400:
                            self.assertGreaterEqual(abs(a[0] - b[0]), 6, (a, b))

    def test_no_rows_or_lines(self):
        for side, condition, stars in self._tiers():
            ordered = sorted(stars, key=lambda s: s[1])
            with self.subTest(side=side, condition=condition):
                for a, b, c in zip(ordered, ordered[1:], ordered[2:], strict=False):
                    # Three neighbours never share a 48 px band (a row) ...
                    self.assertGreaterEqual(c[1] - a[1], 48, (a, b, c))
                    # ... and the middle one is off the line through the outer two (no ladder).
                    t = (b[1] - a[1]) / (c[1] - a[1])
                    self.assertGreaterEqual(abs(a[0] + (c[0] - a[0]) * t - b[0]), 10, (a, b, c))

    def test_spread_over_whole_margin(self):
        for side, condition, stars in self._tiers():
            xs = [x for x, _ in stars]
            ys = sorted(y for _, y in stars)
            with self.subTest(side=side, condition=condition):
                self.assertLessEqual(min(xs), 10)
                self.assertGreaterEqual(max(xs), 90)
                gaps = [b - a for a, b in pairwise(ys)] + [ys[0] + TILE - ys[-1]]
                self.assertLessEqual(max(gaps), 400)
````

`chat/tests/test_selectors.py` (new class `StaffUnreadCountTests`):

````diff
--- a/chat/tests/test_selectors.py
+++ b/chat/tests/test_selectors.py
@@ -1,10 +1,19 @@
 """Selector tests for the chat app."""
 
 from django.contrib.auth.models import AnonymousUser
+from django.db.models import F
 from django.test import TestCase
 
-from chat.models import AuthorRole
-from chat.selectors import dialogs_visible_to, staff_dialog_list, student_unread_count
+from accounts.models import User
+from accounts.tests.helpers import make_staff, make_student
+from chat.models import AuthorRole, Message
+from chat.selectors import (
+    chat_unread_count,
+    dialogs_visible_to,
+    staff_dialog_list,
+    staff_unread_count,
+    student_unread_count,
+)
 from chat.tests.helpers import add_message, make_dialog
 from core.testing import FrozenClockMixin
 from notifications.tests.helpers import make_world
@@ -80,3 +89,118 @@
             self.assertEqual(student_unread_count(self.w.sx), 0)
         with self.assertNumQueries(0):
             self.assertEqual(student_unread_count(AnonymousUser()), 0)
+
+
+class StaffUnreadCountTests(FrozenClockMixin, TestCase):
+    """TASK-018: the "Чаты (n)" count, same rule as the "new" count of the staff chat list."""
+
+    frozen_now = NOW
+
+    @classmethod
+    def setUpTestData(cls):
+        cls.w = make_world()
+        cls.ax_dialog = make_dialog(cls.w.ax_profile)
+        cls.bx_dialog = make_dialog(cls.w.bx_profile)
+        cls.ay_dialog = make_dialog(cls.w.ay_profile)
+
+    def test_counts_own_faculty_only(self):
+        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
+        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
+        add_message(self.bx_dialog, self.w.bx, AuthorRole.STUDENT)
+        for _ in range(4):
+            add_message(self.ay_dialog, self.w.ay, AuthorRole.STUDENT)
+        self.assertEqual(staff_unread_count(self.w.sx), 3)
+        self.assertEqual(staff_unread_count(self.w.sy), 4)
+
+    def test_staff_messages_not_counted(self):
+        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
+        add_message(self.ax_dialog, self.w.sx, AuthorRole.STAFF)
+        sx2 = make_staff("sx2", self.w.fx)
+        add_message(self.bx_dialog, sx2, AuthorRole.STAFF)
+        self.assertEqual(staff_unread_count(self.w.sx), 1)
+        self.assertEqual(staff_unread_count(sx2), 1)
+
+    def test_same_as_staff_list(self):
+        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
+        reply = add_message(self.ax_dialog, self.w.sx, AuthorRole.STAFF)
+        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
+        add_message(self.bx_dialog, self.w.bx, AuthorRole.STUDENT)
+        self.ax_dialog.staff_read_id = reply.pk
+        self.ax_dialog.save(update_fields=["staff_read_id"])
+        listed = sum(d.unread for d in staff_dialog_list(self.w.sx))
+        self.assertEqual(listed, 2)
+        self.assertEqual(staff_unread_count(self.w.sx), listed)
+
+    def test_shared_read_marker(self):
+        sx2 = make_staff("sx2", self.w.fx)
+        first = add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
+        self.assertEqual(staff_unread_count(self.w.sx), 1)
+        self.assertEqual(staff_unread_count(sx2), 1)
+        # One staff member reads the dialog: the count drops for every staff member of the faculty.
+        self.ax_dialog.staff_read_id = first.pk
+        self.ax_dialog.save(update_fields=["staff_read_id"])
+        self.assertEqual(staff_unread_count(self.w.sx), 0)
+        self.assertEqual(staff_unread_count(sx2), 0)
+        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
+        self.assertEqual(staff_unread_count(self.w.sx), 1)
+
+    def test_inactive_student_not_counted(self):
+        add_message(self.bx_dialog, self.w.bx, AuthorRole.STUDENT)
+        self.w.bx.is_active = False
+        self.w.bx.save(update_fields=["is_active"])
+        self.assertEqual(staff_unread_count(self.w.sx), 0)
+
+    def test_staff_without_profile_zero(self):
+        orphan = User.objects.create_user(username="orphan", role=User.Role.STAFF)
+        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
+        self.assertEqual(staff_unread_count(orphan), 0)
+
+    def test_other_roles_zero_without_query(self):
+        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
+        for user in (self.w.ax, self.w.root, AnonymousUser()):
+            with self.subTest(user=str(user)), self.assertNumQueries(0):
+                self.assertEqual(staff_unread_count(user), 0)
+
+    def test_matches_visibility_rule(self):
+        sx2 = make_staff("sx2", self.w.fx)
+        orphan = User.objects.create_user(username="orphan", role=User.Role.STAFF)
+        cx_dialog = make_dialog(self.w.cx_profile)
+        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
+        add_message(self.bx_dialog, self.w.bx, AuthorRole.STUDENT)
+        add_message(cx_dialog, self.w.cx, AuthorRole.STUDENT)
+        add_message(cx_dialog, self.w.sx, AuthorRole.STAFF)
+        add_message(self.ay_dialog, self.w.ay, AuthorRole.STUDENT)
+        self.w.bx.is_active = False
+        self.w.bx.save(update_fields=["is_active"])
+        for user in (self.w.sx, sx2, self.w.sy, orphan):
+            expected = Message.objects.filter(
+                dialog__in=dialogs_visible_to(user),
+                author_role=AuthorRole.STUDENT,
+                id__gt=F("dialog__staff_read_id"),
+            ).count()
+            with self.subTest(user=user.username):
+                self.assertEqual(staff_unread_count(user), expected)
+        self.assertEqual(staff_unread_count(self.w.sx), 2)
+
+    def test_one_query(self):
+        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
+        user = User.objects.get(pk=self.w.sx.pk)
+        with self.assertNumQueries(1):
+            self.assertEqual(staff_unread_count(user), 1)
+        for i in range(5):
+            student = make_student(f"extra{i}", self.w.gx1, f"ST-EX-{i}")
+            dialog = make_dialog(student.student_profile)
+            add_message(dialog, student, AuthorRole.STUDENT)
+        user = User.objects.get(pk=self.w.sx.pk)
+        with self.assertNumQueries(1):
+            self.assertEqual(staff_unread_count(user), 6)
+
+    def test_chat_unread_count_by_role(self):
+        add_message(self.ax_dialog, self.w.ax, AuthorRole.STUDENT)
+        add_message(self.bx_dialog, self.w.sx, AuthorRole.STAFF)
+        self.assertEqual(chat_unread_count(self.w.sx), 1)
+        self.assertEqual(chat_unread_count(self.w.bx), 1)
+        self.assertEqual(chat_unread_count(self.w.ax), 0)
+        with self.assertNumQueries(0):
+            self.assertEqual(chat_unread_count(self.w.root), 0)
+            self.assertEqual(chat_unread_count(AnonymousUser()), 0)
````

`chat/tests/test_views.py` (`NavTests`: 7 new tests; `QueryCountTests`: 1 new test):

````diff
--- a/chat/tests/test_views.py
+++ b/chat/tests/test_views.py
@@ -7,13 +7,14 @@
 from django.contrib.messages import constants
 from django.contrib.messages.storage.base import Message as FrameworkMessage
 from django.db import connection
-from django.test import Client, TestCase
+from django.template import RequestContext, Template
+from django.test import Client, RequestFactory, TestCase
 from django.test.utils import CaptureQueriesContext
 from django.urls import reverse
 
 from accounts.models import User
 from accounts.tests.helpers import make_staff, make_student
-from chat.constants import RATE_LIMIT_MESSAGES
+from chat.constants import CHAT_BADGE_CAP, RATE_LIMIT_MESSAGES
 from chat.models import AuthorRole, Dialog, Message
 from chat.selectors import student_unread_count
 from chat.tests.helpers import add_message, make_dialog
@@ -643,7 +644,69 @@
         self.client.force_login(self.w.sx)
         content = self.client.get("/profile/").content.decode()
         self.assertIn('href="/staff/chats/"', content)
+
+    def test_staff_chat_count(self):
+        # TASK-018: "Чаты (n)" for staff, in the wide and the compact menu.
+        dialog = make_dialog(self.w.ax_profile)
+        add_message(dialog, self.w.ax, AuthorRole.STUDENT)
+        add_message(dialog, self.w.ax, AuthorRole.STUDENT)
+        add_message(dialog, self.w.sx, AuthorRole.STAFF)
+        self.client.force_login(self.w.sx)
+        content = self.client.get("/profile/").content.decode()
+        self.assertEqual(content.count(">Чаты (2)</a>"), 2)
+
+    def test_staff_chat_without_count(self):
+        dialog = make_dialog(self.w.ax_profile)
+        add_message(dialog, self.w.sx, AuthorRole.STAFF)
+        self.client.force_login(self.w.sx)
+        content = self.client.get("/profile/").content.decode()
+        self.assertEqual(content.count(">Чаты</a>"), 2)
+
+    def test_staff_chat_other_faculty_not_counted(self):
+        dialog = make_dialog(self.w.ay_profile)
+        add_message(dialog, self.w.ay, AuthorRole.STUDENT)
+        self.client.force_login(self.w.sx)
+        content = self.client.get("/profile/").content.decode()
+        self.assertEqual(content.count(">Чаты</a>"), 2)
+
+    def test_staff_chat_count_cap(self):
+        dialog = make_dialog(self.w.ax_profile)
+        Message.objects.bulk_create(
+            Message(dialog=dialog, author=self.w.ax, author_role=AuthorRole.STUDENT, text=f"m{i}")
+            for i in range(CHAT_BADGE_CAP + 1)
+        )
+        self.client.force_login(self.w.sx)
+        content = self.client.get("/profile/").content.decode()
+        self.assertEqual(content.count(f">Чаты ({CHAT_BADGE_CAP}+)</a>"), 2)
+
+    def test_staff_chat_count_drops_when_colleague_reads(self):
+        sx2 = make_staff("sx2", self.w.fx)
+        dialog = make_dialog(self.w.ax_profile)
+        add_message(dialog, self.w.ax, AuthorRole.STUDENT)
+        self.client.force_login(self.w.sx)
+        self.assertEqual(self.client.get("/profile/").content.decode().count(">Чаты (1)</a>"), 2)
+        other = Client()
+        other.force_login(sx2)
+        self.assertEqual(other.get(f"/staff/chats/{dialog.public_id}/").status_code, 200)
+        self.assertEqual(self.client.get("/profile/").content.decode().count(">Чаты</a>"), 2)
 
+    def test_student_badge_ignores_unread_for_staff(self):
+        dialog = make_dialog(self.w.ax_profile)
+        add_message(dialog, self.w.ax, AuthorRole.STUDENT)
+        self.client.force_login(self.w.ax)
+        content = self.client.get("/profile/").content.decode()
+        self.assertEqual(content.count(">Чат</a>"), 2)
+
+    def test_badge_tag_empty_for_superuser(self):
+        dialog = make_dialog(self.w.ax_profile)
+        add_message(dialog, self.w.ax, AuthorRole.STUDENT)
+        request = RequestFactory().get("/")
+        request.user = self.w.root
+        rendered = Template("{% load chat_tags %}[{% chat_unread_badge %}]").render(
+            RequestContext(request)
+        )
+        self.assertEqual(rendered, "[]")
+
     def test_badge_includes_chat_reply(self):
         dialog = make_dialog(self.w.ax_profile)
         add_message(dialog, self.w.sx, AuthorRole.STAFF)
@@ -717,6 +780,19 @@
             badge_for_user(user)
             student_unread_count(user)
 
+    def test_staff_page_constant_in_dialogs(self):
+        # TASK-018: the staff badge is one COUNT query, independent of dialogs and messages.
+        self.client.force_login(self.w.sx)
+        add_message(self.dialog, self.w.ax, AuthorRole.STUDENT)
+        one = _query_count(lambda: self.client.get("/profile/"))
+        for i in range(5):
+            student = make_student(f"badge{i}", self.w.gx1, f"REC-B-{i}")
+            d = make_dialog(student.student_profile)
+            add_message(d, student, AuthorRole.STUDENT)
+            add_message(d, student, AuthorRole.STUDENT)
+        six = _query_count(lambda: self.client.get("/profile/"))
+        self.assertEqual(one, six)
+
     def test_header_staff_no_chat_query(self):
         user = User.objects.get(pk=self.w.sx.pk)
         with self.assertNumQueries(0):
````

## 5. Feasibility check

1. **Baseline** — HEAD 094dd55 has 1217 tests (TASK-016-FIX count).
2. **Full change applied** (copy `$TMPDIR/t018`): `manage.py test --parallel` → `Ran 1245 tests … OK`
   (`$TMPDIR/test-t018-full-20261121-104934.log`, 21:50 MSK 21.11); `--parallel 2` → 1245 OK
   (`$TMPDIR/test-t018-p2-20261121-105040.log`, 21:52 MSK). `ruff check .`, `ruff format --check .` clean;
   `makemigrations --check` → No changes; `check` → no issues.
3. **First variant failed one existing test** (reported for the record): with `staff_unread_count` built on
   `dialogs_visible_to`, the serial run (`$TMPDIR/test-t018-serial-20261121-104522.log`, 21:45 MSK) failed
   `campusmap.tests.test_views.MapQueryTests.test_queries_constant` — `AssertionError: 6 not less than or equal
   to 4` (staff profile + faculty + COUNT). The parallel run of the same variant only showed
   `TypeError: cannot pickle 'traceback' object` (a failing test under `--parallel`; run serially to see it).
   D6 fixed it; the final runs above are green.
4. **New tests on HEAD** (`$TMPDIR/test-t018-newtests-on-head-20261121-104413.log`): 11 failures, all expected —
   the 8 star tests that need the new CSS, `NavTests::test_staff_chat_count`, `::test_staff_chat_count_cap`,
   `::test_staff_chat_count_drops_when_colleague_reads`; `test_selectors.py` does not import (`chat_unread_count`
   missing). The others pass on HEAD by design (regression guards: narrow stars unchanged, no star markup,
   other faculty / no unread → "Чаты", student badge, superuser tag, constant page queries).
5. **Mutations**: moving one star to `10% 80px` (a column with `10% 118px`) fails `test_no_columns`,
   `test_no_rows_or_lines` and `test_spread_over_whole_margin`; removing the `author_role` filter fails
   `test_staff_messages_not_counted` and `test_chat_unread_count_by_role`; removing the `is_active` filter fails
   `test_inactive_student_not_counted` and `test_matches_visibility_rule`.
6. **Browser** (runserver on a seeded temporary database, headless Chrome): login (column 410 px) and
   notifications (column 3279 px) at 1024, 1280, 1440, 1920 — stars scattered on both sides, none over the
   column, header or footer; `scrollWidth == clientWidth` everywhere; `body::before` is `display: none` from
   1024; crisp 3 px squares at deviceScaleFactor 2. 360 px: the layers are not generated (`width: auto`, `body::before`
   shown) — unchanged.
7. **Staff badge in the browser**: staff1 with 1 unread → "Чаты (1)"; after 120 more student messages →
   "Чаты (99+)", the staff header still on one line at 1024 px.
8. **Existing query budgets**: `chat/tests/test_views.py::QueryCountTests` (staff list ≤ 6, staff dialog ≤ 10),
   `core/tests/test_home.py::…::test_exact_queries` (student, 14) and `MapQueryTests` (≤ 4) pass unchanged.
9. **Django**: the reverse name `staff_members` (`StaffProfile.faculty`, `related_name="staff_members"`) and
   `RequestContext` rendering of the tag were run on the copy; `bulk_create` of messages uses the model default
   `created_at` (`clock.now`).
10. **Safety** — no `.env` read; temporary databases only; the project tree was not modified by this check.

## 6. Implementation order

F2 + F3 + F4 with the chat tests → F1 with `core/tests/test_stars.py` → `ruff format` on the changed Python
files (never on `docs/`) → verification and visual check.

## 7. Test plan

| AC | Tests |
|---|---|
| AC1 | `core/tests/test_stars.py::WideStarsScatterTests::test_group_sizes_and_values`, `::test_no_columns`, `::test_no_rows_or_lines`, `::test_spread_over_whole_margin`; `WideStarsPlacementTests::test_stars_are_token_coloured_gradients` (token colours, no `url(`), `::test_breakpoints_add_groups`, `::test_no_star_markup_or_inline_style`; `core/tests/test_middleware.py::TemplatesFitPolicyTests` and `core/tests/test_design.py::TokenTests::test_no_colour_literals_outside_tokens` (unchanged) |
| AC2 | `WideStarsPlacementTests::test_layers_beside_content_column` (absolute, top/bottom 0, `right/left: 100%`, width, `pointer-events: none`, `z-index: -1`, `content: ""`), `::test_wide_screens_hide_edge_columns` |
| AC3 | `WideStarsPlacementTests::test_narrow_screens_keep_edge_stars` (old edge stars outside media; the new layers only inside the 64/80/100rem blocks) |
| AC4 | `chat/tests/test_selectors.py::StaffUnreadCountTests::test_counts_own_faculty_only`, `::test_staff_messages_not_counted`, `::test_same_as_staff_list`, `::test_inactive_student_not_counted`, `::test_staff_without_profile_zero`, `::test_matches_visibility_rule`, `::test_one_query`; `chat/tests/test_views.py::NavTests::test_staff_chat_count`, `::test_staff_chat_without_count`, `::test_staff_chat_other_faculty_not_counted`, `::test_staff_chat_count_cap`; `QueryCountTests::test_staff_page_constant_in_dialogs` |
| AC5 | `StaffUnreadCountTests::test_shared_read_marker`, `::test_other_roles_zero_without_query`, `::test_chat_unread_count_by_role`; `NavTests::test_staff_chat_count_drops_when_colleague_reads`, `::test_student_badge_ignores_unread_for_staff`, `::test_badge_tag_empty_for_superuser`; existing `NavTests::test_student_chat_count`, `::test_student_chat_without_count`, `QueryCountTests::test_header_student_four_queries`, `::test_header_staff_no_chat_query` (unchanged) |

Access matrix for the badge:

| User | Badge | Queries |
|---|---|---|
| Student | "Чат (n)", staff messages after `student_read_id` (unchanged) | 1 |
| Staff with profile | "Чаты (n)", student messages after `staff_read_id`, active students of own faculty | 1 |
| Staff without profile | none (0) | 1 |
| Superuser / admin role, anonymous | none | 0 |

Edge cases: 0 → no "( )"; 99 → "(99)"; 100 → "(99+)"; a colleague opens the dialog → drops for everyone;
inactive student → excluded; other faculty → excluded; staff's own replies → excluded; a margin of 16 px
(1024) and 464 px (1920); a page shorter than one tile.

Test count: 1217 → 1245 (+28: stars 10, selectors 10, views 8).

## 8. Verification (UI coder, then Reviewer)

```bash
.venv/bin/python manage.py test --parallel 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/python manage.py test --parallel 2 2>&1 | tee "$TMPDIR/test-p2-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
git status --short
```

If a `--parallel` run ends with `TypeError: cannot pickle 'traceback' object`, a test failed: run
`manage.py test` serially to get its name and report it.

Visual check (temporary seeded database, `runserver`, headless browser; report screenshots):
- Widths 1024, 1280, 1440, 1920 (height 900; long page also 1800): a short page (`/login/`) and a long page
  (`/notifications/` as a student). Stars scattered on both sides, none over the column, header or footer, no
  column/row/ladder; `document.documentElement.scrollWidth === clientWidth`. One zoomed shot at
  deviceScaleFactor 2: crisp squares.
- 360 × 780: identical to HEAD (edge stars and header stars).
- Staff at 1024 and 360 (compact menu): "Чаты (n)"; with ≥ 100 unread student messages "Чаты (99+)", the wide
  header stays on one line at 1024.

Report test counts, log paths and Moscow times; report every failing run with the test name and a traceback
excerpt. Never read `.env`; do not touch `plan.md`.

## 9. Risks

- Taste: star density and positions are a design choice; a change means new frozen positions that still pass
  `core/tests/test_stars.py`.
- Short pages have stars only beside the content column (D3).
- The staff count duplicates the visibility rule as joins (D6); a future change to `students_visible_to` must
  also change `staff_unread_count` — `test_matches_visibility_rule` fails until it does.
- With a classic scrollbar wider than 32 px the right layer would overflow; common scrollbars are 11–17 px.
