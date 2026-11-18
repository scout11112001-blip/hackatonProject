# TASK-013-FIX2: The floor plan fits the screen on wide viewports

Assignee: **UI coder** (thr_pgcwc2dwnn). Request: Team lead, approved by the user (found by the Team lead on 18.11).

## Goal

On wide screens (≥ 48rem) the whole floor plan, the floor buttons and the highlighted room are visible together without scrolling, at 1024 × 768 and larger. The 360 px layout stays exactly as now. No JavaScript.

Problem today (measured 2026-11-18 on a seeded temporary DB, `/map/room/room-101/`, student): at 1024 × 768, 1280 × 800 and 1440 × 900 the plan is 912 × 1477 px (the full content width), from y = 258 to y = 1735; the page is 2642 px high. Screenshot: `docs/process/screenshots/2026-11-18_51_map-wide-1024_student1.jpg`.

## Acceptance criteria

- AC1. At ≥ 48rem the map page uses two columns: the plan on the left; the floor buttons, the legend and the room list on the right (D1).
- AC2. At 1024 × 768, 1280 × 800 and 1440 × 900, with the page scrolled to the top, for a student and for staff, on `/map/room/room-101/` (floor 1) and `/map/room/room-402/` (floor 4): the bottom of `.map-svg` ≤ `innerHeight`; the floor switcher is fully inside the viewport; the highlighted room (`.map-svg .map-current`) is fully inside the viewport; `document.documentElement.scrollWidth === innerWidth`.
- AC3. At 360 × 780 the layout is unchanged: the same order (floor buttons, plan, legend, room list) and the same positions as before the change (measured before: floor switcher y 227–277, `.map-svg` y 285–816, width 328, for a student on `/map/room/room-101/`; tolerance ±2 px).
- AC4. Labels stay readable: the plan is never narrower than 20rem (320 px) at ≥ 48rem, so the 20-unit room labels are ≥ 16 px and the 15-unit landmark/service labels are ≥ 12 px on screen.
- AC5. Pinch-zoom keeps working: the viewport meta tag is unchanged (`width=device-width, initial-scale=1`, no `maximum-scale`, no `user-scalable=no`), and no CSS sets `touch-action: none` on the map.
- AC6. No new JavaScript, no Python changes, no new tokens or colours. Only `campusmap/templates/campusmap/map.html`, `static/css/base.css` and tests change.

## Out of scope

Zoom buttons, route finding, new features. Map colours, the room list look and the plans themselves (TASK-013). The page header.

## Design decisions

- **D1. Two columns, not only a height cap.** Measured with a CSS prototype injected into the page (no file changed), at 1024 × 768:
  - a height cap with the floor buttons above the plan leaves 768 − 258 − 8 = 502 px of height → the plan is 310 px wide; the landmark labels become 11.6 px (below the 12 px reached on a 360 px phone);
  - two columns put the plan right under the `h1` (top at y = 200), so it gets 560 px of height → 346 px wide; labels 17.3 px (rooms) and 13 px (landmarks). The 912 px content width has room for a right column (542 px at 1024), and the room buttons sit next to the plan, so choosing a room keeps the plan in view.
- **D2. DOM order stays the mobile order.** Floor switcher, then plan, then the side content (legend, "Все аудитории", room lists). At ≥ 48rem CSS grid areas place the plan on the left across two rows and the floor switcher and the side content on the right. The reading and tab order (floor links, then room links) stays logical; the SVG is not focusable.
- **D3. Plan size from the viewport height.** At ≥ 48rem: `width: clamp(20rem, calc((100vh - 13rem) * 0.6173), 32rem)`; the height follows from the `viewBox` (400 × 648; 400 / 648 = 0.6173). `13rem` (208 px) = the plan's top at y = 200 (header 108 px, main padding 24 px, `h1` 36 px with 16 px margins) plus an 8 px gap at the bottom. Below a viewport height of about 726 px the 20rem minimum wins and the plan may extend below the fold (readability first). The 32rem cap keeps the plan moderate on very tall screens.
- **D4. Sticky plan.** `.map-plan { position: sticky; top: var(--space-3); align-self: start; }` at ≥ 48rem: when the room list is longer than the screen and the user scrolls, the plan stays visible. The plan's height (≤ `100vh − 13rem`) is smaller than the viewport, so it never hides its own bottom.
- **D5. The hidden hatch `<svg class="map-defs">` stays before the layout wrapper**, outside the grid, so it does not become a grid item.

## Architecture / files

### `campusmap/templates/campusmap/map.html`

Inside `{% else %}` (floors exist), after the `map-defs` SVG, wrap the rest of the content:

```django
  <div class="map-layout">
    <nav class="floor-switcher" aria-label="Этажи"> … unchanged … </nav>
    <div class="map-plan">
      {% if plan %}<svg class="map-svg" …> … unchanged … </svg>
      {% else %}<p>Схемы {{ current_floor }} этажа нет.</p>{% endif %}
    </div>
    <div class="map-side">
      <ul class="map-legend"> … unchanged … </ul>
      <h2>Все аудитории</h2>
      {% for f in floors %} … unchanged h3 + ul.map-room-list … {% endfor %}
    </div>
  </div>
```
Do not change anything inside the moved blocks (texts, classes, attributes, ids).

### `static/css/base.css` (layout only)

Add after the existing map rules:

```css
@media (min-width: 48rem) {
  .map-layout {
    display: grid;
    grid-template-columns: auto minmax(14rem, 1fr);
    grid-template-rows: auto 1fr;
    grid-template-areas:
      "plan floors"
      "plan side";
    column-gap: var(--space-4);
    align-items: start;
  }

  .map-layout > .floor-switcher {
    grid-area: floors;
  }

  .map-plan {
    grid-area: plan;
    position: sticky;
    top: var(--space-3);
  }

  .map-side {
    grid-area: side;
    min-width: 0;
  }

  .map-plan .map-svg {
    width: clamp(20rem, calc((100vh - 13rem) * 0.6173), 32rem);
    margin: 0;
  }

  .map-side > h2:first-of-type {
    margin-top: var(--space-3);
  }
}
```
You may adjust spacing (gaps, the `h2` margin) after the visual check, but keep: the grid areas, `minmax(14rem, 1fr)` for the right column, the `clamp(20rem, calc((100vh - 13rem) * 0.6173), 32rem)` width, and the sticky plan. The existing mobile rule `.map-svg { display: block; width: 100%; height: auto; … }` stays unchanged. Below 48rem the wrappers are plain blocks (no rules), so the phone layout does not change.

Prototype result with exactly these rules (2026-11-18 ~22:20 MSK, injected into the live page in headless Chromium; seeded temporary DB; student and staff):

| Viewport | Plan (top–bottom, width) | Floor switcher | Highlight 101 / 402 | Horizontal scroll |
|---|---|---|---|---|
| 1024 × 768 student | 200–760, 346 | 200–250 | 203–300 / 314–376 | none |
| 1024 × 768 staff | 188–748, 346 | 188–238 | inside | none |
| 1280 × 800 | 200–792, 365 | 200–250 | inside | none |
| 1440 × 900 | 200–892, 427 | 200–250 | inside | none |
| 768 × 1024 (tablet, header wraps) | 232–997, 472; right column 224 px | 232–306 | inside | none |
| 360 × 780 | 285–816, 328 (unchanged) | 227–277 (unchanged) | inside | none |

## Functions

No Python functions change.

## Feasibility check

1. Clean starting point: `git status --short` shows only ` M plan.md` (the Team lead's file; allowed). HEAD `8f469b2 TASK-013-FIX: …`.
2. Referenced objects exist: `campusmap/templates/campusmap/map.html` (`map-defs` SVG, `nav.floor-switcher`, `svg.map-svg` with only a `viewBox`, `ul.map-legend`, `<h2>Все аудитории</h2>`, `ul.map-room-list`, "Схемы … этажа нет."), `static/css/base.css:243` `.map-svg { display: block; width: 100%; height: auto; margin: var(--space-2) 0; }`, `templates/base.html` viewport meta `width=device-width, initial-scale=1`, tokens `--space-3`, `--space-4`.
3. New names are free: `.map-layout`, `.map-plan`, `.map-side` (no match in `static/css/` or templates).
4. Data and migrations: none; `makemigrations --check --dry-run`: "No changes detected".
5. Tools: no new dependency. Headless Chromium via `bb browser-automation` works (used for the measurements).
6. Framework/browser capabilities: CSS grid areas, `clamp()`, `calc()` with `vh`, `position: sticky` in a grid item — all work in Chromium (prototype above).
7. Environment: none.
8. Verification is runnable on the current tree: `check` (no issues), `makemigrations --check` (no changes), `ruff check .` (passed), `ruff format --check .` (190 files formatted), `python manage.py test --parallel 1`: **Ran 1087 tests, OK** (log `/tmp/claude-501/test-20261118-113007.log`, 2026-11-18 ~22:30 MSK).
9. Conflicts: none.
10. Assumptions / blockers: none.

## Test plan

### Traceability

| AC | Tests / checks |
|---|---|
| AC1, AC2 | `campusmap/tests/test_views.py::MapLayoutTests::test_layout_wrappers_and_order`, `core/tests/test_css.py::MapLayoutCssTests::test_wide_two_columns`, `::test_plan_width_from_viewport`; visual measurement (below) |
| AC3 | `MapLayoutTests::test_layout_wrappers_and_order` (DOM order); `MapLayoutCssTests::test_mobile_svg_rule_unchanged`; visual measurement at 360 |
| AC4 | `MapLayoutCssTests::test_plan_width_from_viewport` (min `20rem`) |
| AC5 | `MapLayoutCssTests::test_no_zoom_blocking`; `core/tests/test_views.py` viewport tests (existing) |
| AC6 | `MapLayoutTests::test_defs_outside_layout`; `git status` in the REPORT |

### Access matrix

No view or permission changes. The existing `campusmap/tests/test_views.py::MapAccessTests` must pass unchanged.

### New tests

`campusmap/tests/test_views.py` — new class `MapLayoutTests(TestCase)` with the same `setUpTestData` pattern as `MapViewTests` (student, rooms `room-101`, `room-402`):
- `test_layout_wrappers_and_order`: on `/map/room/room-101/` the content contains `<div class="map-layout">`, `<div class="map-plan">`, `<div class="map-side">` once each, and these indexes are increasing: `map-layout`, `class="floor-switcher"`, `map-plan`, `<svg class="map-svg"`, `map-side`, `class="map-legend"`, `<h2>Все аудитории</h2>`, `class="map-room-list"`.
- `test_defs_outside_layout`: the index of `class="map-defs"` is smaller than the index of `class="map-layout"`.
- `test_floor_without_plan_inside_plan_column`: create `room-501` (floor 5); on `/map/floor/5/` the text "Схемы 5 этажа нет." lies between `<div class="map-plan">` and `<div class="map-side">`.
- `test_no_floors_no_layout`: with no rooms, `/map/` has "Аудиторий пока нет." and no `map-layout`.

`core/tests/test_css.py` — new class `MapLayoutCssTests(SimpleTestCase)` (read `static/css/base.css`; extract the body of every `@media (min-width: 48rem) { … }` block with a small brace-matching helper in the test):
- `test_wide_two_columns`: some 48rem block contains a `.map-layout` rule with `display: grid`, `grid-template-areas` with `"plan floors"` and `"plan side"`, and `minmax(14rem, 1fr)`; and `.map-plan` with `position: sticky`.
- `test_plan_width_from_viewport`: a 48rem block contains `.map-plan .map-svg` with `width: clamp(20rem, calc((100vh - 13rem) * 0.6173), 32rem)`.
- `test_mobile_svg_rule_unchanged`: outside media blocks, the `.map-svg` rule still has `width: 100%` and `height: auto`; no `.map-layout` rule exists outside a 48rem media block.
- `test_no_zoom_blocking`: no CSS file contains `touch-action: none`; `templates/base.html` has `content="width=device-width, initial-scale=1"` and no `maximum-scale` / `user-scalable`.

Existing tests: all `campusmap` tests must pass unchanged (the moved blocks keep their markup). Do not edit any existing test; if one fails, fix the markup.

### Visual check (UI coder; numbers in the REPORT)

Run the app on a temporary DB (role file). For a student and for staff, on `/map/room/room-101/` and `/map/room/room-402/`, at 1024 × 768, 1280 × 800, 1440 × 900, 768 × 1024 and 360 × 780, at scroll 0, report:
```js
const b = s => { const r = document.querySelector(s).getBoundingClientRect(); return [Math.round(r.top), Math.round(r.bottom), Math.round(r.width)]; };
({floors: b(".floor-switcher"), svg: b(".map-svg"), cur: b(".map-svg .map-current"), vh: innerHeight, sw: document.documentElement.scrollWidth, vw: innerWidth})
```
Pass: at ≥ 1024 wide, `svg[1] <= vh`, `floors[1] <= vh`, `cur[1] <= vh`, `sw === vw`; at 360 the numbers match AC3. Screenshots: floor 1 and floor 4 with a highlight at 1024 × 768 (student), 1440 × 900 (staff) and 360 × 780 (student). Also scroll the page at 1024 × 768 until the "4 этаж" room list is visible and confirm the plan stays in view (sticky).

### Edge cases

- A floor without a plan (floor 5): the message sits in the plan column.
- No rooms at all: no layout wrapper.
- Viewport height below ~726 px: the plan keeps its 20rem minimum (may extend below the fold); no horizontal scroll.

## Implementation order

1. Template wrappers (no CSS yet). Run `python manage.py test campusmap --parallel 1` (log): all pass.
2. CSS rules. Visual measurement at all viewports. Adjust spacing only.
3. New tests. Full verification. REPORT.

## Verification

```bash
source .venv/bin/activate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --parallel 1 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log"
python scripts/run_tests_at.py 2026-11-19T00:00:00 2>&1 | tee "$TMPDIR/test-midnight-$(date +%Y%m%d-%H%M%S).log"
ruff check core/tests/test_css.py campusmap/tests/test_views.py
ruff format --check core/tests/test_css.py campusmap/tests/test_views.py
git status --short
```
If any run fails or stalls, even once, put the test name, the Moscow time and the traceback excerpt into the REPORT.

## Risks

- **Short desktop windows** (< ~726 px high): the plan keeps 20rem width and may extend below the fold; the sticky plan then scrolls with the page. Accepted for readability.
- **Header height changes** (a future header change) shift the plan's top; `13rem` would need an update. The visual check catches it.
- **Tablets 48–64rem**: the right column is narrow (224 px at 768 × 1024); the room buttons wrap to two per row. Checked in the prototype; no horizontal scroll.
