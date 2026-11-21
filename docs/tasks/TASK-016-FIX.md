# TASK-016-FIX: systemd paths optional, themed CSRF page, readable eye icon, submit-reset test

Author: Planner. Assignee: UI coder. Status: ready for implementation.
Base: HEAD 30eab5c (TASK-017 committed; clean tree except the Team lead's `plan.md`; do not touch it).

## 1. Goal

Non-blocking notes from the TASK-016/TASK-017 reviews and the Team lead's browser check (21.11).

### Acceptance criteria

| ID | Criterion |
|---|---|
| AC1 | `deploy/systemd/deanery.service`: `ReadWritePaths=-/srv/deanery/private_media -/srv/deanery/private_media_trial` (both prefixed with `-`, systemd then skips a missing path instead of failing the namespace setup), with a one-line comment. The deploy test checks the new line. |
| AC2 | A CSRF failure renders the themed page `templates/403_csrf.html` (extends `base.html`, like `403.html`): h1 "Форма устарела", Russian text (the form is out of date; go back, reload, send again), a "На главную" button. No inline style/script/handlers. Status 403, CSP header present, no CSP violation in the browser. |
| AC3 | The eye icons are redrawn: an almond eye with pointed corners, a round pupil with a highlight pixel (state "password hidden"); the same almond outline with a clear diagonal slash (state "password shown"). Same size (36 × 24 CSS px), same classes, `<rect>` only, `crispEdges`, `currentColor`, `aria-hidden`, `focusable="false"`. Readable at 360 px with deviceScaleFactor 1 and 2. Tap target, toggle behaviour and all TASK-017 tests unchanged. |
| AC4 | A static test proves the submit handler of `static/js/password-toggle.js` calls exactly `setShown(false)` and `setShown` sets `type` by `shown ? "text" : "password"`. The script itself is not changed. |
| AC5 | All verification commands pass; visual check reported (section 8). |

## 2. Out of scope

IPv6 /128 keying of the nginx zones (accepted: no public IPv6). Any other page, script or deploy file. `docs/DEPLOY.md`
(it does not mention `ReadWritePaths`; the Team lead re-installs the unit with runbook step 21 commands).

## 3. Design decisions

- **D1. `-` prefix** (systemd.exec(5): "Paths in ReadWritePaths= … may be prefixed with "-", in which case they
  will be ignored when they do not exist"). With a missing `private_media` the app still starts and only uploads
  fail with a logged error — better than a unit that does not start; the Team lead accepted both prefixes.
- **D2. `403_csrf.html` is Django's own hook.** `django.views.csrf.csrf_failure` (Django 5.2) loads
  `CSRF_FAILURE_TEMPLATE_NAME = "403_csrf.html"` first and renders it with `request=request`, so context
  processors run and `base.html` works (nav, user, messages). Only when the template is missing does it use the
  built-in page with inline CSS. No setting or view is needed. The text does not say "CSRF" (users do not know
  the term).
- **D3. The new icon grid is 18 × 12 cells drawn at 36 × 24 px** (2 CSS px per cell; 4 device px at scale 2).
  12 × 8 cells (3 px) is too coarse for pointed corners and a round pupil. The drawings below were chosen from five
  variants in Chrome: a slash through the pupil (with or without gaps) turned into noise at real size; the
  crossed state therefore keeps the almond outline and drops the pupil, and the slash is 2 cells wide at 45°
  with a 1-cell gap on both sides, so it cuts the outline cleanly.

  Open eye (`icon_eye.html`), `#` = filled cell:

  ```
  ..................
  ......######......
  ....##......##....
  ..##...####...##..
  .#....##..##....#.
  #.....#.####.....#
  #.....######.....#
  .#....######....#.
  ..##...####...##..
  ....##......##....
  ......######......
  ..................
  ```

  Crossed eye (`icon_eye_off.html`):

  ```
  ...##.............
  ....##.#####......
  .....##.....##....
  ..##..##......##..
  .#.....##.......#.
  #.......##.......#
  #........##......#
  .#........##....#.
  ..##.......##.##..
  ....##......##....
  ......######.##...
  ..............##..
  ```

  Each row's runs of `#` are one `<rect height="1">` (the files below are exactly that). You may adjust a few
  cells after your own look, but the drawing tests (F4) must stay green: pointed corners (only rows 5–6 in the
  first and last column), mirrored lids, round pupil (rows 3 and 8: 4 cells; rows 6–7: 6 cells; an empty
  highlight cell), and the slash cells `(3+y, y)`, `(4+y, y)` with empty `(2+y, y)`, `(5+y, y)` in every row.
- **D4. The submit-reset test parses the handler body** with a regular expression and requires it to be exactly
  `setShown(false);`. Mutation check: replacing it with `setShown(true);`, commenting it out, or setting
  `input.type = "text"` in `setShown` each makes the test fail.

## 4. Files and functions

Create: `templates/403_csrf.html`. Replace: `templates/includes/icon_eye.html`,
`templates/includes/icon_eye_off.html`. Change: `deploy/systemd/deanery.service`, `core/tests/test_deploy.py`,
`core/tests/test_errors.py`, `accounts/tests/test_login_page.py`. Diffs are against HEAD 30eab5c; edit by hand, no
git commands.

### F1. `deploy/systemd/deanery.service`

````diff
--- a/deploy/systemd/deanery.service
+++ b/deploy/systemd/deanery.service
@@ -25,7 +25,8 @@
 ProtectControlGroups=true
 RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
 CapabilityBoundingSet=
-ReadWritePaths=/srv/deanery/private_media /srv/deanery/private_media_trial
+# "-": a missing directory (e.g. private_media_trial removed after 2026-11-28) is skipped.
+ReadWritePaths=-/srv/deanery/private_media -/srv/deanery/private_media_trial
 
 [Install]
 WantedBy=multi-user.target
````

### F2. `templates/403_csrf.html` (new)

````django
{% extends "base.html" %}
{% block title %}Форма устарела{% endblock %}
{% block content %}
  <h1>Форма устарела</h1>
  <p>Данные формы не приняты: страница была открыта слишком давно или браузер не сохранил cookie.</p>
  <p>Вернитесь назад, обновите страницу и отправьте форму ещё раз.</p>
  <p><a class="btn" href="{% url 'core:home' %}">На главную</a></p>
{% endblock %}
````

### F3. Icons (whole files)

`templates/includes/icon_eye.html`:

````html
<svg class="icon-eye" viewBox="0 0 18 12" width="36" height="24" shape-rendering="crispEdges" aria-hidden="true" focusable="false"><g fill="currentColor"><rect x="6" y="1" width="6" height="1"/><rect x="4" y="2" width="2" height="1"/><rect x="12" y="2" width="2" height="1"/><rect x="2" y="3" width="2" height="1"/><rect x="7" y="3" width="4" height="1"/><rect x="14" y="3" width="2" height="1"/><rect x="1" y="4" width="1" height="1"/><rect x="6" y="4" width="2" height="1"/><rect x="10" y="4" width="2" height="1"/><rect x="16" y="4" width="1" height="1"/><rect x="0" y="5" width="1" height="1"/><rect x="6" y="5" width="1" height="1"/><rect x="8" y="5" width="4" height="1"/><rect x="17" y="5" width="1" height="1"/><rect x="0" y="6" width="1" height="1"/><rect x="6" y="6" width="6" height="1"/><rect x="17" y="6" width="1" height="1"/><rect x="1" y="7" width="1" height="1"/><rect x="6" y="7" width="6" height="1"/><rect x="16" y="7" width="1" height="1"/><rect x="2" y="8" width="2" height="1"/><rect x="7" y="8" width="4" height="1"/><rect x="14" y="8" width="2" height="1"/><rect x="4" y="9" width="2" height="1"/><rect x="12" y="9" width="2" height="1"/><rect x="6" y="10" width="6" height="1"/></g></svg>
````

`templates/includes/icon_eye_off.html`:

````html
<svg class="icon-eye-off" viewBox="0 0 18 12" width="36" height="24" shape-rendering="crispEdges" aria-hidden="true" focusable="false"><g fill="currentColor"><rect x="3" y="0" width="2" height="1"/><rect x="4" y="1" width="2" height="1"/><rect x="7" y="1" width="5" height="1"/><rect x="5" y="2" width="2" height="1"/><rect x="12" y="2" width="2" height="1"/><rect x="2" y="3" width="2" height="1"/><rect x="6" y="3" width="2" height="1"/><rect x="14" y="3" width="2" height="1"/><rect x="1" y="4" width="1" height="1"/><rect x="7" y="4" width="2" height="1"/><rect x="16" y="4" width="1" height="1"/><rect x="0" y="5" width="1" height="1"/><rect x="8" y="5" width="2" height="1"/><rect x="17" y="5" width="1" height="1"/><rect x="0" y="6" width="1" height="1"/><rect x="9" y="6" width="2" height="1"/><rect x="17" y="6" width="1" height="1"/><rect x="1" y="7" width="1" height="1"/><rect x="10" y="7" width="2" height="1"/><rect x="16" y="7" width="1" height="1"/><rect x="2" y="8" width="2" height="1"/><rect x="11" y="8" width="2" height="1"/><rect x="14" y="8" width="2" height="1"/><rect x="4" y="9" width="2" height="1"/><rect x="12" y="9" width="2" height="1"/><rect x="6" y="10" width="6" height="1"/><rect x="13" y="10" width="2" height="1"/><rect x="14" y="11" width="2" height="1"/></g></svg>
````

### F4. Tests

`core/tests/test_deploy.py` (`SystemdUnitTests::test_hardening`):

````diff
--- a/core/tests/test_deploy.py
+++ b/core/tests/test_deploy.py
@@ -320,7 +320,8 @@
             "ProtectControlGroups=true",
             "RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX",
             "CapabilityBoundingSet=",
-            "ReadWritePaths=/srv/deanery/private_media /srv/deanery/private_media_trial",
+            # TASK-016-FIX: "-" skips a missing directory instead of failing the unit.
+            "ReadWritePaths=-/srv/deanery/private_media -/srv/deanery/private_media_trial",
         ):
             self.assertIn(line, lines)
         self.assertNotIn("ProtectSystem=full", lines)
````

`core/tests/test_errors.py` (new class `CsrfFailurePageTests`):

````diff
--- a/core/tests/test_errors.py
+++ b/core/tests/test_errors.py
@@ -3,7 +3,8 @@
 from pathlib import Path
 
 from django.conf import settings
-from django.test import RequestFactory, TestCase
+from django.test import Client, RequestFactory, TestCase
+from django.urls import reverse
 from django.views.defaults import server_error
 
 from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
@@ -58,3 +59,27 @@
         self.assertNotIn("{%", content)
         template = (Path(settings.BASE_DIR) / "templates/500.html").read_text()
         self.assertNotIn("{% extends", template)
+
+
+class CsrfFailurePageTests(TestCase):
+    """TASK-016-FIX: a themed CSRF failure page instead of Django's page with inline CSS."""
+
+    def test_csrf_failure_uses_project_template(self):
+        client = Client(enforce_csrf_checks=True)
+        response = client.post(reverse("accounts:login"), {"username": "a", "password": "b"})
+        self.assertEqual(response.status_code, 403)
+        self.assertTemplateUsed(response, "403_csrf.html")
+        self.assertTemplateUsed(response, "base.html")
+        content = response.content.decode()
+        self.assertIn("<h1>Форма устарела</h1>", content)
+        self.assertIn("Вернитесь назад, обновите страницу и отправьте форму ещё раз.", content)
+        self.assertIn('href="/static/css/theme.css"', content)
+        self.assertNotIn("<style", content)
+        self.assertNotIn("CSRF", content)
+        self.assertIn("Content-Security-Policy", response)
+
+    def test_template_has_no_inline_code(self):
+        text = (Path(settings.BASE_DIR) / "templates" / "403_csrf.html").read_text(encoding="utf-8")
+        for forbidden in ("<style", "style=", "<script", "javascript:"):
+            self.assertNotIn(forbidden, text)
+        self.assertNotRegex(text, r"\son[a-z]+\s*=")
````

`accounts/tests/test_login_page.py` (new `LoginToggleStaticTests::test_submit_resets_to_password`, the viewBox
check in `::test_icons`, new class `EyeIconDrawingTests`):

````diff
--- a/accounts/tests/test_login_page.py
+++ b/accounts/tests/test_login_page.py
@@ -85,6 +85,20 @@
         for forbidden in ("innerHTML", "eval(", "aria-label", "fetch(", "localStorage"):
             self.assertNotIn(forbidden, js)
 
+    def test_submit_resets_to_password(self):
+        # TASK-016-FIX: the submit handler must call setShown(false) (Reviewer's missed mutation).
+        js = (BASE / "static/js/password-toggle.js").read_text(encoding="utf-8")
+        match = re.search(
+            r'input\.form\.addEventListener\(\s*"submit",\s*function\s*\(\)\s*\{(.*?)\}\s*\);',
+            js,
+            re.DOTALL,
+        )
+        self.assertIsNotNone(match)
+        self.assertEqual(match.group(1).strip(), "setShown(false);")
+        setter = re.search(r"function setShown\(shown\)\s*\{(.*?)\n    \}", js, re.DOTALL)
+        self.assertIsNotNone(setter)
+        self.assertIn('input.type = shown ? "text" : "password";', setter.group(1))
+
     def test_css(self):
         base = (BASE / "static/css/base.css").read_text(encoding="utf-8")
         self.assertRegex(base, r"\.password-toggle\[hidden\]\s*\{\s*display:\s*none;")
@@ -98,8 +112,52 @@
     def test_icons(self):
         for name in ("icon_eye.html", "icon_eye_off.html"):
             svg = (BASE / "templates/includes" / name).read_text(encoding="utf-8")
+            # TASK-016-FIX: 18 x 12 grid drawn at 36 x 24 CSS px (2 px per cell).
+            self.assertIn('viewBox="0 0 18 12" width="36" height="24"', svg)
             self.assertIn('shape-rendering="crispEdges"', svg)
             self.assertIn('fill="currentColor"', svg)
             self.assertIn("<rect", svg)
             for forbidden in ("style=", "<path", "<script", "href="):
                 self.assertNotIn(forbidden, svg)
+
+
+class EyeIconDrawingTests(SimpleTestCase):
+    """TASK-016-FIX: an almond eye with a round pupil; the "shown" state is crossed out."""
+
+    @staticmethod
+    def _cells(name):
+        svg = (BASE / "templates/includes" / name).read_text(encoding="utf-8")
+        cells = set()
+        for x, y, w, h in re.findall(
+            r'<rect x="(\d+)" y="(\d+)" width="(\d+)" height="(\d+)"/>', svg
+        ):
+            for dx in range(int(w)):
+                for dy in range(int(h)):
+                    cells.add((int(x) + dx, int(y) + dy))
+        return cells
+
+    def test_open_eye_shape(self):
+        cells = self._cells("icon_eye.html")
+        # Pointed corners: the outermost columns hold only the two middle rows.
+        self.assertEqual({y for x, y in cells if x == 0}, {5, 6})
+        self.assertEqual({y for x, y in cells if x == 17}, {5, 6})
+        # Symmetric lids: the outline is mirrored left/right.
+        outline = {(x, y) for x, y in cells if x < 6 or x > 11 or y in (1, 10)}
+        self.assertEqual(outline, {(17 - x, y) for x, y in outline})
+        # Round pupil: 4 wide at the top and bottom rows, 6 wide in the middle, a highlight gap.
+        pupil = {(x, y) for x, y in cells if 6 <= x <= 11 and 3 <= y <= 8}
+        self.assertEqual({x for x, y in pupil if y == 3}, {7, 8, 9, 10})
+        self.assertEqual({x for x, y in pupil if y == 8}, {7, 8, 9, 10})
+        self.assertEqual({x for x, y in pupil if y in (6, 7)}, set(range(6, 12)))
+        self.assertLess(len(pupil), 32)  # not a filled square: the highlight is empty
+
+    def test_crossed_eye_has_diagonal(self):
+        cells = self._cells("icon_eye_off.html")
+        for y in range(12):
+            self.assertIn((3 + y, y), cells, y)
+            self.assertIn((4 + y, y), cells, y)
+            self.assertNotIn((2 + y, y), cells, y)
+            self.assertNotIn((5 + y, y), cells, y)
+        # The same pointed corners as the open eye.
+        self.assertEqual({y for x, y in cells if x == 0}, {5, 6})
+        self.assertEqual({y for x, y in cells if x == 17}, {5, 6})
````

## 5. Feasibility check

1. **Baseline** — HEAD 30eab5c copy (`git archive`, no `.env`): `manage.py test --parallel` → `Ran 1212 tests …
   OK` (`$TMPDIR/test-t016fix-head-20261121-012735.log`).
2. **Full change applied** (copy `$TMPDIR/t016fixc`): `--parallel` → `Ran 1217 tests … OK`
   (`$TMPDIR/test-t016fix-20261121-012638.log`, 12:27 MSK 21.11); `--parallel 2` → 1217 OK
   (`$TMPDIR/test-t016fix-p2-20261121-012938.log`, 12:30 MSK). `ruff check .`, `ruff format --check .` clean;
   `makemigrations --check` → No changes.
3. **New tests on HEAD** — 5 failures + 1 error, all expected: `test_hardening` (old line),
   `CsrfFailurePageTests` ×2 (no template: Django's page with `<style>`; file missing), `test_icons` (viewBox),
   `EyeIconDrawingTests` ×2. `test_submit_resets_to_password` passes on HEAD (the script is already right) and
   fails on the three mutations of D4 (`$TMPDIR/test-t016fix-newtests-on-head-20261121-012824.log`).
4. **Browser** (runserver on a seeded temporary database, headless Chrome): login at 360 px, scale 1 and 2,
   both states — the open eye reads as an eye with a round pupil, the crossed state as a crossed-out eye; toggle
   44 px high, behaviour unchanged. CSRF: deleting the `csrftoken` cookie and submitting the login form → 403,
   h1 "Форма устарела", the themed background and button, zero CSP violations.
5. **Django source** — `django/views/csrf.py::csrf_failure` (5.2.19): `loader.get_template("403_csrf.html")`,
   `t.render(request=request)`; fallback to the built-in page only on `TemplateDoesNotExist`.
6. **systemd** — not available locally (macOS); semantics from systemd.exec(5). The Team lead runs
   `systemd-analyze verify` when installing the unit (runbook step 21 commands).
7. **Safety** — no `.env` read; temporary databases only; the project tree was not modified by this check.

## 6. Implementation order

F1 + its test → F2 + `CsrfFailurePageTests` → F3 + icon tests → the submit-reset test → `ruff format` on the
changed test files (never on `docs/`) → verification and visual check.

## 7. Test plan

| AC | Tests |
|---|---|
| AC1 | `core/tests/test_deploy.py::SystemdUnitTests::test_hardening` (changed: the `-` line; still exactly one `ReadWritePaths=` line) |
| AC2 | `core/tests/test_errors.py::CsrfFailurePageTests::test_csrf_failure_uses_project_template` (403, `403_csrf.html` and `base.html` used, h1/text, theme CSS link, no `<style`, no "CSRF", CSP header), `::test_template_has_no_inline_code`; `core/tests/test_middleware.py::TemplatesFitPolicyTests` (unchanged, now also scans the new template) |
| AC3 | `accounts/tests/test_login_page.py::EyeIconDrawingTests::test_open_eye_shape`, `::test_crossed_eye_has_diagonal`, `LoginToggleStaticTests::test_icons` (+ viewBox/size), `LoginToggleMarkupTests::test_two_pixel_icons` (unchanged) |
| AC4 | `LoginToggleStaticTests::test_submit_resets_to_password` |

Edge cases: CSRF failure for an anonymous user (login form) — the page renders without nav; a missing
`private_media_trial` (systemd skips it); icons at scale 1 and 2.

Test count: 1212 → 1217 (+5).

## 8. Verification (UI coder, then Reviewer)

```bash
.venv/bin/python manage.py test --parallel 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/python manage.py test --parallel 2 2>&1 | tee "$TMPDIR/test-p2-$(date +%Y%m%d-%H%M%S).log" | tail -3
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
git status --short
```

Visual check (temporary seeded database, `runserver`, headless browser; report screenshots):
- Login at 360 × 780 with deviceScaleFactor 1 and 2, and 1024 × 768: both toggle states; the icon must read as an
  eye / a crossed-out eye.
- CSRF page: open `/login/`, delete the `csrftoken` cookie, submit → the themed 403 page at 360 and 1024; no CSP
  violation in the console. Also once as a signed-in student (e.g. a chat or request form after deleting the
  cookie): nav is shown.

Report test counts, log paths and Moscow times; report every failing run with the test name and a traceback
excerpt. Never read `.env`; do not touch `plan.md`.

## 9. Risks

- The icon is a taste decision: the drawings passed the Team lead's criteria in Chrome; the user may still ask
  for changes — then only the two icon files and `EyeIconDrawingTests` change.
- `-` on `private_media` hides a missing upload directory at start; uploads then fail and are logged.
