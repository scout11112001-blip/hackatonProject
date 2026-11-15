# TASK-008-FIX: random-token-safe page assertions, landmark label fit, compact header menu

Author: Planner. Status: ready for implementation.
Base commit: `caf7601`. Related specs: `docs/tasks/TASK-008.md` (map geometry D6), `docs/tasks/TASK-007.md` (nav badge). Screenshots: `docs/process/screenshots/2026-11-15_23..26_*.jpg`.

No new features. Each fix is minimal and has a regression test that fails without it; the visual result (header at 360 px and wide, every map floor) is checked by the Team lead.

---

## 1. Acceptance criteria
| ID | Criterion |
|---|---|
| AC1 | No test asserts a needle on a full HTML page that a random part of the page (CSRF token, UUIDs) can contain by chance with a probability above 1e-6 per run. `test_staff_group_list_scoped` asserts on the group URLs and on `response.context`. Every hit of the sweep (section 4.1) has a verdict; the unsafe ones are fixed. |
| AC2 | The fixed scope assertion still detects a leak (automated mutation test) and is not fooled by a CSRF token that contains «GY» (automated test). |
| AC3 | Every landmark label fits inside its shape with at least `LABEL_PADDING` = 8 user units on each side, on every floor, whatever font the phone uses: labels whose estimated width exceeds the available width get `textLength` = available width and `lengthAdjust="spacingAndGlyphs"`. Room numbers and label sizes are unchanged. |
| AC4 | Below `48rem` the nav is a «Меню» disclosure (`<details>`/`<summary>`); at `48rem` and wider the full inline nav is shown as now. No JavaScript. |
| AC5 | A student with unread notifications sees «Уведомления (N)» as a link outside the closed menu. The badge is computed once per page (3 queries, as before). |
| AC6 | The menu lists the same items as the wide nav for each role (student, staff, superuser), one per line, tap targets ≥ 2.75rem; «Выйти» stays a POST form with CSRF. Links to the current page have `aria-current="page"`. Anonymous pages render as before (an empty nav, no menu). |

## 2. Out of scope
Room list under the map, map zoom, new features, the pixel-art theme, chat (TASK-009).

## 3. Files
Change only:
- tests: `schedule/tests/test_views.py`, `accounts/tests/test_views.py`, `petitions/tests/test_views.py`, `notifications/tests/test_views.py`, `campusmap/tests/test_layout.py`, `campusmap/tests/test_views.py`, `core/tests/test_css.py`; new `core/tests/test_nav.py`
- `campusmap/layout.py`, `campusmap/templates/campusmap/map.html`
- `templates/base.html`, new `templates/includes/site_nav_items.html`, `static/css/base.css`
- `README.md` (one line in "Test & lint", see 4.1.4)

No models, migrations, settings or dependencies.

---

## 4. Fixes

### 4.1 Item 1 — page assertions that a random token can match

#### 4.1.1 Why it fails
Every authenticated page contains the masked CSRF token (64 random characters from `[A-Za-z0-9]`, in the logout form). Probability that a fixed ASCII-alphanumeric needle of length k appears in it: k = 2 → 63/62² ≈ 1.6 %; k = 3 → 2.6e-4; k = 4 → 4.1e-6; k ≥ 5 → < 1e-7. Petition pages also contain UUIDs (hex). A needle that contains any character outside `[A-Za-z0-9]` (markup such as `href="…"`, quotes, `<`, `/`, spaces, Cyrillic) can never match the token. `assertNotIn` with a matching needle fails at random (flaky); `assertIn` passes even when the expected element is missing (hides bugs).

Rule for this task and for future tests (add it to README "Test & lint", 4.1.4): an assertion on a full page uses a needle with at least one character outside `[A-Za-z0-9]` (preferably exact markup, e.g. `href="/staff/schedule/12/"`) or at least 6 ASCII alphanumerics, or asserts on `response.context`.

#### 4.1.2 Sweep (done by the Planner on `caf7601`, 817 tests)
Method: (a) static AST scan of all `*/tests/test_*.py` for `assertIn`/`assertNotIn`/`assertContains`/`assertNotContains` with a literal needle of ≤ 4 characters or only `[A-Za-z0-9]`; (b) a full instrumented run that recorded every such assertion with a non-literal needle too, when the needle matches `^[A-Za-z0-9_-]{1,8}$` and the haystack is a page (> 300 characters). Result:

| # | Location | Assertion (needle) | Haystack | Verdict |
|---|---|---|---|---|
| 1 | `schedule/tests/test_views.py:182` | `assertNotIn("GY", content)` | staff group list page | **fix** (1.6 % flaky) |
| 2 | `schedule/tests/test_views.py:180-181` | `assertIn("GX1"/"GX2", content)` | same page | **fix** (3 alnum; replace together with #1) |
| 3 | `schedule/tests/test_views.py:343-344` | `assertIn("205"/"101", content)` | week page | **fix** (3 digits; also in dates/times) |
| 4 | `notifications/tests/test_views.py:557` | `assertIn("x", content)` | staff announcements page | **fix** (always true) |
| 5 | `petitions/tests/test_views.py:405` | `assertIn(self.student.group.name, content)` = «GX» | staff petition detail | **fix** (2 alnum) |
| 6 | `accounts/tests/test_views.py:176` | `assertIn("<li>", full_content)` | staff student list | **fix** (always true: the nav has `<li>`) |
| 7 | `petitions/tests/test_views.py:51-53, 98-104, 366-392` | short ids (8 hex, e.g. `84468ccb`) | petition pages | safe (8 alnum: < 1e-12 vs the token; < 1e-8 vs a UUID) |
| 8 | `accounts/tests/test_views.py:87-90, 115` | `REC-A`, `REC-B`, `REC-C` | pages | safe (`-` and uppercase `REC` cannot occur in the token or in a hex UUID) |
| 9 | `campusmap/tests/test_views.py:181` | `assertNotIn("personal", content)` | map page | safe (8 letters: < 1e-12) |
| 10 | `core/tests/test_views.py:33` | `"<nav"` | home | safe (markup) |
| 11 | `notifications/tests/test_views.py:467` | `"<br>"` | feed | safe (markup; `base.html` has no `<br>`) |
| 12 | `petitions/tests/test_views.py:199` | `"errorlist"` | form page | safe (9 letters; rendered only with errors) |
| 13 | `schedule/tests/test_views.py:341-342` | `"<del"`, `"<ins"` | week page | safe (markup) |
| 14 | `academics/tests/test_models.py:614`, `accounts/tests/test_models.py:54`, `campusmap/tests/test_layout.py:90,95,100`, `notifications/tests/test_views.py:49,115`, `schedule/tests/test_revalidation.py:117`, `schedule/tests/test_validation.py:35,41,48,49,258`, `university/tests/test_models.py:79,91` | short needles | lists, dicts, error messages — not pages | safe (no random content) |

#### 4.1.3 Fixes
1. `schedule/tests/test_views.py::ScheduleViewsTests::test_staff_group_list_scoped`:
```python
response = self.client.get("/staff/schedule/")
content = response.content.decode()
for group in (self.group_x1, self.group_x2):
    self.assertIn(f'href="/staff/schedule/{group.pk}/"', content)
self.assertNotIn(f'href="/staff/schedule/{self.group_y.pk}/"', content)
self.assertEqual(set(response.context["groups"]), {self.group_x1, self.group_x2})
```
(`schedule/templates/schedule/staff_group_list.html:7` renders `href="{% url 'schedule:staff_group_week' group.pk %}"` = `/staff/schedule/<pk>/`; the closing quote stops `/1/` from matching `/12/`.)
2. `schedule/tests/test_views.py::ChangeRenderingTests::test_change_rendering`: replace `assertIn("205", content)` with `assertIn('data-room-code="room-205"', content)` and `assertIn("101", content)` with `assertIn('<del class="room" data-room-code="room-101">', content)` (rooms `room-101` / `room-205` from the class setup; markup from `lesson_item.html`). Keep the comments «new room number» / «old room number».
3. `notifications/tests/test_views.py::StaffAnnouncementsViewTests::test_service_error_shown_as_form_error`: replace the last assertion with `self.assertEqual(response.context["form"].non_field_errors(), ["x"])`.
4. `petitions/tests/test_views.py::StaffPagesTests::test_detail_shows_student_info_and_actions`: `assertIn(f"<p>{self.student.group.name}</p>", content)` (`staff_detail.html:6`).
5. `accounts/tests/test_views.py::AccessViewsTests::test_staff_list_empty_state_markup` (line 176): replace `assertIn("<li>", full_content)` with `assertIn(f'href="{reverse("accounts:staff_student_detail", args=[self.student_a.student_profile.pk])}"', full_content)` (`student_a` is in `group_x` of `staff_x`'s faculty).

#### 4.1.4 README
In "Test & lint" add one bullet: «Assertions on whole pages: use exact markup (e.g. `href="/staff/schedule/12/"`) or `response.context`; never a short alphanumeric needle — the page contains a random CSRF token.»

### 4.2 Item 2 — landmark labels fit their cells (`campusmap/layout.py`, `map.html`)
Decision: keep `LANDMARK_LABEL_SIZE = 15` (12.3 px at 360 px, TASK-008 D6) and clamp the rendered text length with SVG `textLength` + `lengthAdjust="spacingAndGlyphs"`. Why: the server cannot know the phone's font metrics; `textLength` makes the browser scale the actual glyph run to exactly the given length, so the padding is guaranteed for any font. A smaller font would drop «Лестница» below 10 px (the only single-cell long label: 72 units minus padding leaves 56); abbreviations or icons would change the content. Only labels that need it are clamped; room numbers are never clamped (3 digits ≈ 39 units < 56).

Add to `layout.py`:
```python
LABEL_PADDING = 8          # user units on each side of a label
LABEL_CHAR_EM_NUM = 13     # estimated glyph width = 0.65 em (generous for Cyrillic)
LABEL_CHAR_EM_DEN = 20


def estimated_label_width(label: str, size: int) -> int:
    return (len(label) * LABEL_CHAR_EM_NUM * size + LABEL_CHAR_EM_DEN - 1) // LABEL_CHAR_EM_DEN


def label_text_length(label: str, rect: Rect, size: int) -> int | None:
    available = rect.width - 2 * LABEL_PADDING
    return available if estimated_label_width(label, size) > available else None
```
`MapShape` gets `text_length: int | None = None` (last field). In `floor_plan`, landmark shapes: `MapShape("landmark", lm.label, rect, text_length=label_text_length(lm.label, rect, LANDMARK_LABEL_SIZE))` with `rect = span_rect(lm.cells)`. Room shapes unchanged (`text_length=None`).
Results on the current layout: «Лестница» → estimate 78 > 56 → `textLength="56"`; «Вход» 39 ≤ 56 → none; «Столовая» 78, «Библиотека» 98, «Деканат» 69 ≤ 132 (two cells) → none.
`map.html`, the `<text>` element: add `{% if s.text_length %} textLength="{{ s.text_length }}" lengthAdjust="spacingAndGlyphs"{% endif %}` after `dominant-baseline="central"`. All values stay integers.

### 4.3 Item 3 — compact header menu (`base.html`, include, CSS)

Decision: two renderings of ONE item list — the existing inline nav for wide screens and a `<details class="site-menu">` disclosure for narrow screens — switched by the existing `48rem` media query with `display: none`. Why: `<details>`/`<summary>` is a native disclosure (keyboard: Enter/Space; announced as expanded/collapsed; named by the summary text) and needs no JavaScript. A single `<details>` that is forced open on wide screens needs `::details-content`, which cannot be verified here without a browser and is missing in older phone browsers (the nav would disappear); the checkbox hack has worse semantics. The duplicated markup comes from one include, so the two lists cannot drift; `display: none` also hides the inactive copy from assistive technology.

New `templates/includes/site_nav_items.html` = the current `<ul class="site-nav-list">…</ul>` from `base.html` (same items and order per role, same logout form), with two changes:
- no `{% notifications_badge %}` call inside (it uses the `badge` variable set in `base.html`);
- each link marks the current page: `{% url 'accounts:profile' as nav_url %}<li><a href="{{ nav_url }}"{% if request.path == nav_url %} aria-current="page"{% endif %}>Профиль</a></li>` (same pattern for every link; `nav_url` is reassigned before each link).

`templates/base.html`, the header becomes:
```django
<header class="site-header">
  <a class="site-title" href="{% url 'core:home' %}">Цифровой деканат будущего</a>
  {% if user.is_student %}{% notifications_badge as badge %}{% endif %}
  <nav class="site-nav site-nav--wide" aria-label="Основная навигация">
    {% block nav %}{% if user.is_authenticated %}{% include "includes/site_nav_items.html" %}{% endif %}{% endblock %}
  </nav>
  {% if user.is_authenticated %}
  <div class="site-nav-compact">
    <details class="site-menu">
      <summary class="site-menu-toggle">Меню</summary>
      <nav class="site-nav" aria-label="Основная навигация">
        {% include "includes/site_nav_items.html" %}
      </nav>
    </details>
    {% if badge %}<a class="site-menu-badge" href="{% url 'notifications:feed' %}">Уведомления ({{ badge }})</a>{% endif %}
  </div>
  {% endif %}
</header>
```
Notes: the badge tag runs once (before both lists); for staff, superuser and anonymous `badge` is unset → no badge link and no query. Anonymous users get the same empty `<nav>` as today. Keep the `class` attribute on `<details>`: `academics/tests/test_views.py:243` counts bare `<details>` tags.

`static/css/base.css`: append
```css
.site-nav--wide {
  display: none;
}

.site-nav-compact {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2) var(--space-3);
  margin-top: var(--space-2);
}

.site-menu-toggle,
.site-menu-badge {
  display: inline-block;
  min-height: 2.75rem;
  line-height: 2.75rem;
}

.site-menu-toggle {
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  cursor: pointer;
}

.site-menu[open] {
  flex-basis: 100%;
}

.site-menu .site-nav-list {
  flex-direction: column;
  gap: 0;
}

.site-menu .site-nav-list a,
.site-menu .site-nav-list button {
  display: block;
  min-height: 2.75rem;
  line-height: 2.75rem;
}

@media (min-width: 48rem) {
  .site-nav--wide {
    display: block;
  }

  .site-nav-compact {
    display: none;
  }
}
```
Closed header at 360 px: line 1 = site title, line 2 = «Меню» + «Уведомления (N)». Open menu: one item per line.

---

## 5. Test plan

### 5.1 Rules
- Use existing helpers; `FrozenClockMixin` where the class already uses it. Page assertions follow the rule in 4.1.1.
- Run the full suite at least 3 times (section 7); save every log; report any failure by test name, Moscow time and traceback excerpt.

### 5.2 Traceability and regression evidence
| AC | Test (file::class::method) | Fails before fix because |
|---|---|---|
| AC1 | fixes 4.1.3 #1–#5 (existing test names) | (#1 flaky; #4, #6 always true — see AC2-style checks below) |
| AC2 | `schedule/tests/test_views.py::ScheduleViewsTests::test_scope_check_detects_leak` | (guard: proves the new needle catches a leak) |
| AC2 | `…::ScheduleViewsTests::test_scope_check_ignores_csrf_token` | old `assertNotIn("GY", content)` fails when the token contains «GY» |
| AC1 | `notifications/tests/test_views.py::StaffAnnouncementsViewTests::test_service_error_shown_as_form_error` (fixed) | old assertion passes without the error |
| AC3 | `campusmap/tests/test_layout.py::LayoutTests::test_landmark_labels_fit_with_padding`, `test_stairs_label_clamped`, `test_rooms_never_clamped` | no `text_length`; «Лестница» estimate 78 > 56 |
| AC3 | `campusmap/tests/test_views.py::MapViewTests::test_stairs_label_has_text_length` | attribute missing |
| AC4 | `core/tests/test_nav.py::NavMarkupTests::test_student_menu`, `test_staff_menu`, `test_superuser_menu` | no `<details class="site-menu">` |
| AC4 | `core/tests/test_css.py::BaseCssTests::test_compact_nav_rules` | rules missing |
| AC5 | `core/tests/test_nav.py::NavBadgeTests::test_badge_outside_menu`, `test_no_badge_without_unread`, `test_no_badge_for_staff`, `test_badge_computed_once` | no badge link outside; tag call inside the list |
| AC6 | `core/tests/test_nav.py::NavMarkupTests::test_logout_form_in_both_lists`, `test_current_page_marked`, `test_anonymous_unchanged` | no second form; no `aria-current` |

### 5.3 Test details
- `test_scope_check_detects_leak`: `with mock.patch("schedule.views.groups_visible_to", return_value=StudyGroup.objects.select_related("program__faculty").order_by("name")):` GET `/staff/schedule/` as `staff_x` → `assertIn(f'href="/staff/schedule/{self.group_y.pk}/"', content)` (the leaked group IS found by the new needle).
- `test_scope_check_ignores_csrf_token`: `with mock.patch("django.middleware.csrf._mask_cipher_secret", return_value="GY" * 32):` GET `/staff/schedule/` as `staff_x` → `assertIn("GY" * 32, content)` (the token now contains the old needle), and the three new assertions of `test_staff_group_list_scoped` pass. (`_mask_cipher_secret` is the module function `get_token` calls; `django/middleware/csrf.py:59,114`.)
- Mutation check for the `REPORT`: temporarily change `test_staff_group_list_scoped` to log in as `staff_y`; it must fail on the `assertIn` for `group_x1`. Revert. Write the observed failure in the `REPORT`.
- `LayoutTests` (`campusmap/tests/test_layout.py`):
  - `test_landmark_labels_fit_with_padding`: for floors 1–9 and every landmark shape of `floor_plan(floor, [], None)`: `min(estimated_label_width(label, LANDMARK_LABEL_SIZE), shape.text_length or 10**6) <= shape.rect.width - 2 * LABEL_PADDING`.
  - `test_stairs_label_clamped`: the «Лестница» shape has `text_length == CELL_WIDTH - 2 * LABEL_PADDING` (56).
  - `test_rooms_never_clamped`: room shapes have `text_length is None`; `estimated_label_width("888", ROOM_LABEL_SIZE) <= CELL_WIDTH - 2 * LABEL_PADDING`.
  - Keep `test_label_sizes` unchanged (sizes did not change). Update the old `test_labels_fit` to call `estimated_label_width` (or delete it if fully covered by the new test — say which in the `REPORT`).
- `MapViewTests::test_stairs_label_has_text_length` (`campusmap/tests/test_views.py`): GET `/map/floor/1/` → SVG part contains `textLength="56" lengthAdjust="spacingAndGlyphs">Лестница</text>`; `>Вход</text>` element has no `textLength`; no room label has `textLength`.
- `core/tests/test_nav.py` (new). Helpers inside the module: `_wide(content)` = text between `<nav class="site-nav site-nav--wide"` and the next `</nav>`; `_menu(content)` = text between `<details class="site-menu">` and `</details>`; `_hrefs(part)` = `re.findall(r'<a href="([^"]+)"', part)`.
  - `NavMarkupTests(TestCase)` (users from `accounts/tests/helpers.py`; superuser via `create_superuser`):
    - `test_student_menu`: GET `/profile/` as a student → exactly one `<details class="site-menu">`, `<summary class="site-menu-toggle">Меню</summary>`; `_hrefs(_wide) == _hrefs(_menu) == ["/profile/", "/schedule/", "/map/", "/grades/", "/requests/", "/notifications/"]`.
    - `test_staff_menu`: same with `["/profile/", "/staff/schedule/", "/map/", "/staff/requests/", "/staff/announcements/", "/staff/students/"]`.
    - `test_superuser_menu`: `["/profile/"]` in both.
    - `test_logout_form_in_both_lists`: each part contains `<form class="site-nav-logout" method="post" action="/logout/">` and `name="csrfmiddlewaretoken"`; a POST to `/logout/` still logs out (302 to `/login/`).
    - `test_current_page_marked`: on `/profile/` `content.count('href="/profile/" aria-current="page"') == 2` and `content.count('aria-current="page"') == 2`.
    - `test_anonymous_unchanged`: GET `/login/` → no `site-menu`, no `site-menu-badge`; contains `<nav class="site-nav site-nav--wide" aria-label="Основная навигация">`.
  - `NavBadgeTests(FrozenClockMixin, TestCase)` (`frozen_now = "2026-11-11 12:00"`; announcement via `notifications/tests/helpers.py::make_announcement`, university audience):
    - `test_badge_outside_menu`: student with 1 unread → `<a class="site-menu-badge" href="/notifications/">Уведомления (1)</a>` present and its index is after `content.index("</details>")`.
    - `test_no_badge_without_unread`, `test_no_badge_for_staff`: no `site-menu-badge`.
    - `test_badge_computed_once`: `with mock.patch("notifications.templatetags.notifications_tags.badge_for_user", wraps=badge_for_user) as spy:` GET `/profile/` as the student → `spy.call_count == 1`.
- `core/tests/test_css.py::BaseCssTests::test_compact_nav_rules`: `base.css` matches `r"\.site-nav--wide\s*\{\s*display:\s*none;"` (outside the media block, i.e. before the `@media (min-width: 48rem)` that contains `.site-nav-compact`), and the regex `r"@media \(min-width: 48rem\)\s*\{\s*\.site-nav--wide\s*\{\s*display:\s*block;\s*\}\s*\.site-nav-compact\s*\{\s*display:\s*none;"`.
- Existing tests that must keep passing unchanged: `notifications/tests/test_views.py::NavTests::*`, `::QueryCountTests::test_badge_exactly_three_queries`, `test_profile_page_counter_constant`, `campusmap/tests/test_views.py::MapViewTests::test_current_floor_marked` (counts `aria-current="page"` on `/map/floor/2/`; the nav link `/map/` is not the current path there), `campusmap/tests/test_views.py::MapNavTests::*`, `academics/tests/test_views.py:243` (`<details>` count), `core/tests/test_views.py::HomeViewTests::*`, `petitions/tests/test_views.py::NavigationTests::*`.

### 5.4 Access matrix
No access rules change. The nav items per role are asserted in `NavMarkupTests` (student / staff / superuser / anonymous).

### 5.5 Settings branches / query count
No settings change. Query count: `test_badge_computed_once` + the existing `test_profile_page_counter_constant` and `test_badge_exactly_three_queries`.

---

## 6. Implementation order
1. Item 1: fixes 4.1.3 and the two new schedule tests; run them; do the mutation check; README bullet.
2. Item 2: regression tests (must fail), then `layout.py` + `map.html`.
3. Item 3: `core/tests/test_nav.py` and the CSS test (must fail), then include, `base.html`, CSS.
4. `ruff format` on changed/new Python files only; section 7; `REPORT` to the Reviewer with the regression evidence and the mutation-check output. Do not commit.

## 7. Verification
```bash
source .venv/bin/activate
export DEBUG=true
TS=$(TZ=Europe/Moscow date +%Y%m%d-%H%M%S)
python manage.py check
python manage.py makemigrations --check --dry-run
for i in 1 2 3; do python manage.py test 2>&1 | tee "$TMPDIR/test-$TS-run$i.log" | grep -E "^Ran|^OK|^FAILED"; done
python scripts/run_tests_at.py 2026-11-17T23:59:59 2>&1 | tee "$TMPDIR/test-$TS-at-2359.log"
python scripts/run_tests_at.py 2026-11-18T00:00:00 2>&1 | tee "$TMPDIR/test-$TS-at-0000.log"
DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
  python manage.py check --deploy --fail-level WARNING
ruff check . && ruff format --check .
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
export DATABASE_URL="sqlite:///$TMPDIR/task008fix.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task008fix-private" DEMO_PASSWORD='Local-Demo-Pass-2026!'
rm -f "$TMPDIR/task008fix.sqlite3"
python manage.py migrate && python manage.py seed_demo && python manage.py seed_demo
git status --short
```
`REPORT`: output tails, test counts of the 3 runs (was 817), log file names, any failed run by test name and Moscow time, mutation-check output, `git status`.

## 8. Feasibility check (2026-11-15 18:20 MSK on `caf7601`)
1. Clean start — `git status --short` → only ` M plan.md`. OK.
2. Referenced objects — `test_staff_group_list_scoped` (`schedule/tests/test_views.py:177-182`), class attributes `group_x1`, `group_x2`, `group_y`, `staff_x`, `staff_y`; `ChangeRenderingTests` rooms `room-101`, `room-205` (`:250-251`) and assertions `:341-344`; `staff_group_list.html:7` URL markup; `StaffGroupListView` context name `groups` (`schedule/views.py`, `context_object_name = "groups"`); `groups_visible_to` imported into `schedule.views`; `notifications/tests/test_views.py:548-557`; `petitions/tests/test_views.py:400-405` + `staff_detail.html:6`; `accounts/tests/test_views.py:173-176`, `student_a` (`:34`), URL `accounts:staff_student_detail`; `django.middleware.csrf._mask_cipher_secret` (`.venv/…/django/middleware/csrf.py:59`, called by `get_token` at `:114`); `campusmap/layout.py` (`MapShape`, `floor_plan`, `LANDMARK_LABEL_SIZE = 15`, `CELL_WIDTH = 72`), `map.html` `<text>` line 24; `campusmap/tests/test_layout.py::test_labels_fit` (`:67-73`); `templates/base.html:14-45` (nav, `{% block nav %}`, badge tag in the student branch, logout form); no template overrides `{% block nav %}`; `.site-nav-list` and the `48rem` media query in `base.css`; `notifications.templatetags.notifications_tags.badge_for_user`. OK.
3. No collisions — no `templates/includes/`, no `core/tests/test_nav.py`, no CSS classes `site-nav--wide`, `site-nav-compact`, `site-menu*`, no names `LABEL_PADDING`, `estimated_label_width`, `label_text_length`, `text_length`. OK.
4. Migrations — none; `makemigrations --check` clean (8a).
5. Tools — unchanged. OK.
6. Framework — `simple_tag … as var` sets the variable in the current context, `{% if %}` does not push a new context and `{% include %}` sees parent variables, so one badge call serves both lists. `get_token` masks via the module-level `_mask_cipher_secret`, so the patch in 5.3 controls the rendered token. The token alphabet is `CSRF_ALLOWED_CHARS` = ASCII letters + digits (`csrf.py`), length 64. SVG `textLength`/`lengthAdjust="spacingAndGlyphs"` are SVG 1.1 text attributes (no browser available here to render; the Team lead checks visually). OK.
7. Environment — nothing new. OK.
8. Verification runnable — see 8a.
9. Conflicts — none.
10. Assumptions / blockers — none.

### 8a. Verification results on the current tree
Logs `$TMPDIR/test-20261115-182607-t008fix-feas*.log` and the sweep run `$TMPDIR/test-20261115-182047-t008fix-sweep.log`.
- `check` → no issues; `makemigrations --check --dry-run` → «No changes detected».
- `test` → `Ran 817 tests … OK`; instrumented sweep run (18:20 MSK) → 817 OK; `run_tests_at.py 2026-11-17T23:59:59` → 817 OK; `run_tests_at.py 2026-11-18T00:00:00` → 817 OK. No failed or stalled runs.
- `check --deploy --fail-level WARNING` → no issues (1 silenced); `ruff check .` → all passed; `ruff format --check .` → 160 files already formatted; CI YAML ok.
- `seed_demo` twice on a temporary DB and PRIVATE_MEDIA_ROOT → OK (second run «Notifications ready: 0 announcements.»).

## 9. Risks
- Duplicate nav markup: tests that count nav links must count within one list (`_wide`/`_menu`); existing tests were checked (5.3, last bullet).
- `textLength` compresses «Лестница» by about 15 % in a typical font; acceptable for the layout stage, the UI stage may replace it with an icon.
- Flaky tests elsewhere that use other random content (e.g. future pages with tokens) are prevented only by the README rule; the Reviewer applies it.
