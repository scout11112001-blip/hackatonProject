# TASK-013: Floor plans v3, final map look, no change reasons, small UI fixes

Assignee: **UI coder** (thr_pgcwc2dwnn). Request: Team lead, approved by the user.

## Goal

1. Make the floor plans plausible: two staircases, no storage rooms, a separate wardrobe and a small security post at a moved entrance, one toilet per floor (М/Ж alternating), and a door from every room to the corridor.
2. Give the map its final look: an orange highlighted room, distinct landmarks and service spaces, a room list of pixel buttons.
3. Stop showing the reasons of lesson changes anywhere. The field stays in the database and the admin and becomes optional.
4. Fix three small UI defects: the file input text is cut, the wide header wraps at 1024 px, and the scrollbar is not themed.

## Acceptance criteria

Floor plans (`university/building.py`):
- AC1. No space is labelled "Склад" on any floor.
- AC2. Every floor has exactly two "Лестница" landmarks: one at `STAIRS` `Rect(164, 4, 72, 80)` (the top end of the corridor) and one at `STAIRS_BOTTOM` `Rect(164, 572, 72, 72)` (the bottom end). The constant `BOTTOM_CENTRE` is removed.
- AC3. "Вход" exists only on floor 1. It is a landmark next to the corridor, at the outer east wall: `Rect(236, 500, 160, 72)` (D1).
- AC4. "Гардероб" (`Rect(308, 572, 88, 72)`) and "Охрана" (`Rect(236, 572, 72, 72)`) on floor 1 are separate service spaces next to the entrance. "Охрана" has 45% of its old area (5184 instead of 11520). "Столовая" is one rectangle `Rect(4, 452, 160, 192)`, not a polygon. The only multi-part space left is room 210.
- AC5. **Access rule.** Every room shares a wall of at least `DOOR_MIN = 24` units with the corridor, except the rooms in `INNER_ROOMS = {"211"}`. Every landmark and service space, except the two staircases, shares a wall of at least 24 units with the corridor or with the "Вход" space (D2).
- AC6. Toilets: exactly one service space per floor whose label starts with "Туалет". It is "Туалет М" on floors 1 and 3 and "Туалет Ж" on floors 2 and 4. All four are at the same `TOILET = Rect(4, 404, 160, 48)` (one riser).
- AC7. The existing rules still hold: full coverage of outline minus corridor without overlaps, integer geometry, NNN room numbers with the floor digit, the same 39 room numbers (9/10/10/10), the demo rooms (101, 114, 205, 212, 308, 315, 402) on their floors, every shape at least 48 units high, room labels never clamped.

Map page (`/map/…`):
- AC8. Highlighted room: the shape is filled with the orange accent, has a light pixel frame (thicker than other frames) and the number in the dark "on accent" colour. The `map-current` class, `aria-current="location"` and the `<title>Аудитория NNN</title>` stay.
- AC9. Landmarks have a yellow label and a dashed yellow frame. Service spaces have a muted lilac label, a dotted lilac frame and a diagonal hatch fill. Rooms have a solid light frame and a light label. The legend swatches use the same classes, so they show exactly these styles.
- AC10. The corridor has no label (no `<text>` other than one per shape).
- AC11. The room list under the map is a grid of pixel buttons per floor, each at least 44×44 px. The current room's button is marked (class `map-current`, `aria-current="location"`, orange like the highlight). Rooms not on a plan keep the note "нет на схеме".

Change reasons:
- AC12. No page shows a lesson change reason: schedule today/week (student), the staff group week, the home "Занятия" card and the notifications feed. The change itself stays visible ("Отменено", "Перенесено на …", "Перенесено с …", "Замена аудитории", "Замена преподавателя", the crossed-out old room or teacher and the new one).
- AC13. `LessonChange.reason` is optional: `blank=True`, the check constraint `schedule_change_reason_required` is removed (migration `schedule/0005_lessonchange_reason_optional`). The admin still shows and edits the field. Demo seeds keep their reasons.

Small fixes:
- AC14. Request form at 360 px: the file input takes the full content width of the form, and the browser's own text next to the button ("No file chosen" / "Файл не выбран") is not cut.
- AC15. At 1024 px and at 1280 px the wide header is one line: the brand, every wide nav item (including "Выйти") and, for students, the notifications button. Check for a student with the chip "50+" and the nav item "Чат (99+)", and for staff (8 nav items).
- AC16. Thin square scrollbar in the theme colours for the page and any scroll container: standard `scrollbar-width: thin` and `scrollbar-color`, plus `::-webkit-scrollbar` rules. On devices with a fine pointer and hover, the thumb is transparent until the pointer is over the page or the scroll area, and it is visible while dragging. Scrollbars are never hidden completely (no `scrollbar-width: none`, no `display: none` on scrollbar pseudo-elements).

General:
- AC17. No new JavaScript, no new Python dependency, `static/js/chat.js` unchanged. All colours stay in `tokens.css` (TASK-012 AC1). Every new text/background pair meets WCAG AA (Contrast table).
- AC18. README "## Map" describes the new plans: two staircases, the entrance, one toilet per floor, the access rule, and the services list without "Склад".

## Out of scope

Zoom, route finding, several buildings, a "news only" page, new features. Changes to the map view logic (`campusmap/views.py`) and to `campusmap/layout.py` (not needed: the layout reads the plans). Hiding a reason-only edit of a change from the unread counter (see Risks).

## Design decisions

- **D1. Entrance.** The bottom end of the corridor now holds the second staircase, so the entrance moves to the east wing, next to the corridor (`Rect(236, 500, 160, 72)`, the old "Склад" and lower "Медпункт" area). Visitors enter from the outer east wall straight into the corridor. The bottom-right corner below the entrance (y 572–644) is split into "Охрана" (a small post, 72 wide) and "Гардероб" (88 wide). Both open onto the entrance hall. The wardrobe is next to the entrance, not inside the canteen. The canteen takes the full bottom of the west wing.
- **D2. Door rule.** "Shares a wall" means a common boundary segment of at least `DOOR_MIN = 24` user units. The corridor is 72 units wide (about 3 m), so 24 units is about 1 m: a door fits. A shorter contact (for example 8 or 16 units, as 206, 207 and 308 have today) is not a door. Under this rule the current plans also break it at rooms 206 (8 units), 207 and 308 (16 units). The new plans fix them as well. Rooms are split along the corridor: every space in a wing is a full-width horizontal strip, except the 210/211 pair (211 is the inner room of 210, a user decision) and the Охрана/Гардероб pair (they open onto the entrance).
- **D3. Toilets in one riser.** `TOILET = Rect(4, 404, 160, 48)` on every floor. The label is "Туалет М" (odd floors) or "Туалет Ж" (even floors).
- **D4. Plans (exact data; replace the plan part of `university/building.py` from `VIEWBOX_WIDTH = 400` up to `def plan_for`).** The checker script `$TMPDIR/t013/plan.py` (Planner's prototype) and the prototype test run below confirm coverage, no overlap, the door rule, labels and heights.

```python
VIEWBOX_WIDTH = 400
VIEWBOX_HEIGHT = 648
OUTLINE = Rect(4, 4, 392, 640)
CORRIDOR = Rect(164, 84, 72, 488)
STAIRS = Rect(164, 4, 72, 80)
STAIRS_BOTTOM = Rect(164, 572, 72, 72)
TOILET = Rect(4, 404, 160, 48)
DOOR_MIN = 24  # shortest shared wall that counts as access (a door)
INNER_ROOMS = frozenset({"211"})  # rooms reached through another room


def _r(x: int, y: int, w: int, h: int) -> tuple[Rect, ...]:
    return (Rect(x, y, w, h),)


def _room(number: str, x: int, y: int, w: int, h: int) -> Space:
    return Space(ROOM, number, _r(x, y, w, h))


def _landmark(label: str, x: int, y: int, w: int, h: int) -> Space:
    return Space(LANDMARK, label, _r(x, y, w, h))


def _service(label: str, x: int, y: int, w: int, h: int) -> Space:
    return Space(SERVICE, label, _r(x, y, w, h))


def _stairs() -> tuple[Space, Space]:
    return (
        Space(LANDMARK, "Лестница", (STAIRS,)),
        Space(LANDMARK, "Лестница", (STAIRS_BOTTOM,)),
    )


def _toilet(floor: int) -> Space:
    return Space(SERVICE, "Туалет М" if floor % 2 == 1 else "Туалет Ж", (TOILET,))


FLOOR_PLANS: dict[int, tuple[Space, ...]] = {
    1: (
        *_stairs(),
        _toilet(1),
        _room("101", 4, 4, 160, 112),
        _room("102", 4, 116, 160, 80),
        _room("103", 4, 196, 160, 64),
        _room("104", 4, 260, 160, 72),
        _room("105", 4, 332, 160, 72),
        _landmark("Столовая", 4, 452, 160, 192),
        _room("106", 236, 4, 160, 108),
        _room("107", 236, 112, 160, 72),
        _room("108", 236, 184, 160, 72),
        _room("114", 236, 256, 160, 108),
        _service("Кафедра", 236, 364, 160, 72),
        _service("Медпункт", 236, 436, 160, 64),
        _landmark("Вход", 236, 500, 160, 72),
        _service("Охрана", 236, 572, 72, 72),
        _service("Гардероб", 308, 572, 88, 72),
    ),
    2: (
        *_stairs(),
        _toilet(2),
        _landmark("Деканат", 4, 4, 160, 120),
        _room("201", 4, 124, 160, 72),
        _room("202", 4, 196, 160, 64),
        _room("203", 4, 260, 160, 72),
        _room("205", 4, 332, 160, 72),
        _room("206", 4, 452, 160, 192),
        _room("207", 236, 4, 160, 108),
        _room("208", 236, 112, 160, 76),
        Space(
            ROOM,
            "210",
            (Rect(236, 188, 160, 128), Rect(236, 316, 80, 96)),
            ((236, 188), (396, 188), (396, 316), (316, 316), (316, 412), (236, 412)),
        ),
        _room("211", 316, 316, 80, 96),
        _room("212", 236, 412, 160, 120),
        _service("Кафедра", 236, 532, 160, 112),
    ),
    3: (
        *_stairs(),
        _toilet(3),
        _room("301", 4, 4, 160, 120),
        _room("302", 4, 124, 160, 64),
        _room("303", 4, 188, 160, 64),
        _room("304", 4, 252, 160, 80),
        _room("305", 4, 332, 160, 72),
        _room("306", 4, 452, 160, 96),
        _room("308", 4, 548, 160, 96),
        _landmark("Библиотека", 236, 4, 160, 200),
        _room("310", 236, 204, 160, 104),
        _room("312", 236, 308, 160, 120),
        _service("Кафедра", 236, 428, 160, 104),
        _room("315", 236, 532, 160, 112),
    ),
    4: (
        *_stairs(),
        _toilet(4),
        _room("401", 4, 4, 160, 128),
        _room("402", 4, 132, 160, 72),
        _room("403", 4, 204, 160, 64),
        _room("404", 4, 268, 160, 64),
        _room("405", 4, 332, 160, 72),
        _room("406", 4, 452, 160, 192),
        _room("407", 236, 4, 160, 112),
        _room("408", 236, 116, 160, 96),
        _room("409", 236, 212, 160, 144),
        _service("Кафедра", 236, 356, 160, 96),
        _room("410", 236, 452, 160, 96),
        _service("Архив", 236, 548, 160, 96),
    ),
}
```
  Keep the module docstring, `Rect`, `ROOM`/`LANDMARK`/`SERVICE`, `Space` and the three functions after `FLOOR_PLANS` unchanged. Update the docstring sentence about non-rectangular spaces if it names the canteen (it does not today). Room 210 keeps its old polygon (an existing view test checks it). The data is copied verbatim; it is formatted by ruff already (checked).
- **D5. Map colour tokens** (`static/css/tokens.css`; replace the current map tokens):

  | Token | Value | Use |
  |---|---|---|
  | `--color-map-highlight` | `#ffd98a` | light frame of the current room (stroke) |
  | `--color-map-highlight-fill` | `#ff9f2e` | fill of the current room (the orange accent) |
  | `--color-map-highlight-text` | `#2b1300` | number of the current room ("on accent") |
  | `--color-map-room-fill` | `rgba(36, 22, 78, 0.88)` | unchanged |
  | `--color-map-corridor-fill` | `rgba(90, 63, 163, 0.35)` | unchanged |
  | `--color-map-room-stroke` | `#f3ecff` | room frame |
  | `--color-map-landmark` | `#ffd25e` | landmark label and dashed frame |
  | `--color-map-service` | `#b8a6e8` | service label and dotted frame |
  | `--color-map-hatch` | `#5a3fa3` | hatch lines of service spaces |
  | `--color-map-label-halo` | `#170d33` | dark outline behind service labels |
  | `--color-scroll-thumb` | `#b8a6e8` | scrollbar thumb |
  | `--color-scroll-thumb-hover` | `#ff9f2e` | scrollbar thumb on hover |

  The track is `transparent` (a keyword, allowed outside tokens.css).
- **D6. Map styles** (theme.css; base.css keeps only the layout, sizes and the dash arrays):
  - Rooms: fill `--color-map-room-fill`, stroke `--color-map-room-stroke`, stroke-width 2, label `--color-text`.
  - Landmarks: fill `--color-map-room-fill`, stroke `--color-map-landmark`, stroke-width 2, `stroke-dasharray: 8 4` (square dashes, `stroke-linecap: butt`), label `--color-map-landmark`.
  - Services: fill `url(#map-hatch)`, stroke `--color-map-service`, stroke-width 2, `stroke-dasharray: 2 4`, label `--color-map-service` with `paint-order: stroke; stroke: var(--color-map-label-halo); stroke-width: 4px; stroke-linejoin: round` (D7).
  - Current room (`.map-current rect`, `.map-current polygon`): fill `--color-map-highlight-fill`, stroke `--color-map-highlight`, stroke-width 6. `.map-current .map-room-label`: fill `--color-map-highlight-text`, bold. The thicker frame and the dark number mark the room without relying on hue.
  - Corridor: as now (fill `--color-map-corridor-fill`), no label.
  - Hatch pattern: in `campusmap/map.html`, inside the `{% else %}` branch (when floors exist) and before the floor switcher, add one hidden SVG:
    ```html
    <svg class="map-defs" width="0" height="0" aria-hidden="true" focusable="false"><defs><pattern id="map-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect class="map-hatch-bg" width="8" height="8"/><rect class="map-hatch-line" width="2" height="8"/></pattern></defs></svg>
    ```
    Theme: `.map-hatch-bg { fill: var(--color-map-room-fill); }`, `.map-hatch-line { fill: var(--color-map-hatch); }`. Layout (base.css): `.map-defs { position: absolute; width: 0; height: 0; overflow: hidden; }`. Do not use `display: none` on it (some browsers do not render patterns from a `display: none` SVG). The legend swatches use the same `url(#map-hatch)` through the `.map-service` class.
  - Manifest storage leaves `url(#map-hatch)` unchanged (prototype below). Update the TASK-012 test that allows only `url("../…")` (see the Test plan).
- **D7. Contrast of the map.** See the Contrast table. The muted lilac label over a hatch line gives only 3.61:1. The dark halo (`paint-order: stroke`) keeps the label at 8.46:1 against `#170d33`.
- **D8. Room list markup** (`campusmap/map.html`):
  ```django
  <ul class="map-room-list">
    {% for r in f.rooms %}
    <li><a class="btn map-room-btn{% if r.is_current %} map-current{% endif %}" href="{{ r.url }}"{% if r.is_current %} aria-current="location"{% endif %}>{{ r.number }}</a>{% if not r.on_map %} <span class="map-room-off">нет на схеме</span>{% endif %}</li>
    {% endfor %}
  </ul>
  ```
  Layout: `.map-room-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(5rem, 1fr)); gap: 0.75rem; }` (the gap leaves room for the 6 px box-shadow frames); `.map-room-btn { display: flex; align-items: center; justify-content: center; min-height: 2.75rem; }`; `.map-room-off` small muted text on its own line under the button. Theme: `a.map-current.map-room-btn` gets the primary (orange) button look with `--color-on-accent` text. Remove the old `a.map-current` colour/underline rules and the old `.map-room-list a` and flex rules that conflict.
- **D9. Legend text** (`campusmap/map.html`): landmarks "Вход, лестницы, деканат, библиотека, столовая"; services "Служебные помещения: гардероб, туалет, охрана, кафедра и другие". The room entry stays "Аудитория".
- **D10. Change reasons.** Templates do not render `change.reason`. The feed item of a lesson change has an empty body (`body=""`), so the feed template shows no body paragraph. The admin is unchanged. The `reason` field stays (`max_length=200`, `blank=True`). Seed data keeps its reasons (visible in the admin).
- **D11. Change labels after the reason is removed** (`schedule/includes/lesson_item.html`): the `<p class="lesson-change">` contains only the label, with no trailing period: "Отменено", "Перенесено на 19 ноября, 5 пара (16:15)", "Перенесено с 17 ноября, 1 пара", "Замена аудитории", "Замена преподавателя". Exact change: replace `{% endif %}. Причина: {{ item.change.reason }}</p>` with `{% endif %}</p>`. The compact include (home card) is unchanged: it shows no reason already.
- **D12. Wide header at ≥ 1024 px.** The UI coder chooses how, within these limits: nav link text stays ≥ 0.9375rem (15 px) in the body font; tap targets stay ≥ 44 px high; nothing is hidden or truncated; no change to the nav markup in `site_nav_items.html` except CSS classes. Allowed means: smaller gaps, the site title on two lines at all widths (as on the phone), a smaller logo gap, moving "Выйти" visually next to the notifications button with CSS only. Below 64rem (1024 px) the header may wrap as today; the menu (< 48rem) is unchanged.
- **D13. File input.** `.form input[type="file"]` is full width (`width: 100%`, `box-sizing: border-box`, `display: block`). Its `::file-selector-button` keeps the panel button look but uses smaller horizontal padding and margin so that the native text fits at 360 px. If the text still does not fit, the button may use `--font-size-tag`. Do not replace the native input (no JS, no label tricks).
- **D14. Scrollbars** (theme.css; colours via tokens):
  ```css
  html { scrollbar-width: thin; scrollbar-color: var(--color-scroll-thumb) transparent; }
  * { scrollbar-width: thin; }
  ::-webkit-scrollbar { width: 8px; height: 8px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--color-scroll-thumb); border-radius: 0; }
  ::-webkit-scrollbar-thumb:hover, ::-webkit-scrollbar-thumb:active { background: var(--color-scroll-thumb-hover); }
  @media (hover: hover) and (pointer: fine) {
    html { scrollbar-color: transparent transparent; }
    html:hover { scrollbar-color: var(--color-scroll-thumb) transparent; }
    ::-webkit-scrollbar-thumb { background: transparent; }
    :hover::-webkit-scrollbar-thumb { background: var(--color-scroll-thumb); }
    ::-webkit-scrollbar-thumb:hover, ::-webkit-scrollbar-thumb:active { background: var(--color-scroll-thumb-hover); }
  }
  ```
  You may adjust selectors after checking in Chromium. Keep these properties: thin, square, transparent track, lilac thumb, orange on hover/active, hidden thumb only inside the `(hover: hover) and (pointer: fine)` query and shown on `:hover`. `scrollbar-color` is inherited, so scroll containers get it from `html`. There are no scroll containers today (`grep overflow static/css` finds none); if you add one, it gets the same rules. No transitions (TASK-012 D15).
- **D15. Tests that assert old behaviour** are updated, each with a `# TASK-013: <reason>` comment (list in the Test plan). No other test may change without a reason in the REPORT.

## Architecture / files

- `university/building.py`: plan data (D4).
- `university/tests/test_building.py`: rewritten checks (Test plan).
- `campusmap/templates/campusmap/map.html`: hatch defs (D6), room list (D8), legend text (D9).
- `campusmap/tests/test_layout.py`, `campusmap/tests/test_views.py`: updated and new tests.
- `schedule/models.py`: `reason = models.CharField("причина", max_length=200, blank=True)`; remove the `CheckConstraint(condition=~models.Q(reason=""), name="schedule_change_reason_required")`.
- New `schedule/migrations/0005_lessonchange_reason_optional.py`: create it with `python manage.py makemigrations schedule --name lessonchange_reason_optional`. Expected operations (prototype): `RemoveConstraint(model_name="lessonchange", name="schedule_change_reason_required")` and `AlterField(model_name="lessonchange", name="reason", field=models.CharField(blank=True, max_length=200, verbose_name="причина"))`, dependency `("schedule", "0004_lessonchange_updated_at")`. Run `ruff format` on the new migration file only.
- `schedule/templates/schedule/includes/lesson_item.html`: D11.
- `notifications/sources.py`: in `LessonChangeSource.to_item`, `body=obj.reason` → `body=""`.
- `schedule/tests/test_validation.py`, `schedule/tests/test_views.py`, `notifications/tests/test_feed.py`, `notifications/tests/test_views.py`, `core/tests/test_home.py`: updated and new tests.
- `static/css/tokens.css`, `static/css/base.css`, `static/css/theme.css`: D5, D6, D8, D12, D13, D14.
- `core/tests/test_css.py`, `core/tests/test_design.py`: updated and new tests.
- `README.md`: "## Map" section (AC18).

No changes to `campusmap/layout.py`, `campusmap/views.py`, `schedule/admin.py`, `schedule/demo.py`, `university/models.py`, `static/js/`.

## Functions

There are no new production functions. The changes are data, templates, CSS and one model field. New test helpers (private, in `university/tests/test_building.py`):

```python
def _shared_wall(a: Rect, b: Rect) -> int:
```
- Length of the common boundary of two non-overlapping rectangles: if `a.x + a.width == b.x` or `b.x + b.width == a.x`, return `max(0, min(a.y + a.height, b.y + b.height) - max(a.y, b.y))`; elif `a.y + a.height == b.y` or `b.y + b.height == a.y`, return the same for x; else 0.
- Unit tests: `test_shared_wall_helper` (side by side 40 units → 40; corner touch → 0; apart → 0; above/below with 24 overlap → 24).

```python
def _space_wall(space: Space, rects: list[Rect]) -> int:
```
- `max((_shared_wall(p, r) for p in space.parts for r in rects), default=0)`.

## Pages to check visually (UI coder)

| Page | Viewports | Role |
|---|---|---|
| `/map/floor/1/` … `/map/floor/4/` | 360×780, 1024×768 | student |
| `/map/room/room-101/` (floor 1, highlight) and `/map/room/room-402/` (floor 4, highlight) | 360, 1024 | student |
| `/map/room/room-210/` (polygon highlight) | 360 | student |
| Room list under the map (grid, current room, a room not on the plan: create one on the temporary DB, for example 199) | 360, 1024 | student |
| `/schedule/`, `/schedule/week/` with changes (demo data has 8 changes) | 360, 1024 | student |
| Staff group week with changes | 1024 | staff |
| `/` home "Занятия" card | 360 | student |
| `/notifications/` (a lesson change item without a body) | 360 | student |
| Request form with the file input (any `/requests/new/<id>/`) | 360 (Chromium), 1024 | student |
| Wide header | 1024×768 and 1280×800 | student with "50+" and "Чат (99+)" (create unread items on the temporary DB or patch nothing: 51 announcements and 100 staff chat messages), staff |
| Scrollbar: any long page, pointer over and away from the page | 1024 | student |

Header check (AC15) in the browser: `new Set([...document.querySelectorAll('.site-nav--wide li')].map(e => Math.round(e.getBoundingClientRect().top))).size === 1`, and for students the vertical centre of `.site-notif` is within 8 px of the centre of the first `li`. Put the numbers in the REPORT.

File input check (AC14): screenshot of the field at 360 px; the native text is fully visible. Put the input width and the form content width in the REPORT.

## Contrast (new pairs; WCAG 2.x, panel composite `#29184f` = worst case)

| Foreground | Background | Ratio | Need |
|---|---|---|---|
| highlight text `#2b1300` | highlight fill `#ff9f2e` | 8.57 | 4.5 |
| highlight frame `#ffd98a` | room fill (panel) / darkest sky | 11.45 / 14.10 | 3 |
| highlight fill `#ff9f2e` | room fill (panel) | 7.55 | 3 |
| landmark `#ffd25e` | room fill (panel) / hatch line `#5a3fa3` | 10.78 / 5.47 | 4.5 |
| service label `#b8a6e8` | room fill (panel) / halo `#170d33` | 7.12 / 8.46 | 4.5 |
| (rejected without halo) service label | hatch line `#5a3fa3` | 3.61 | 4.5, fails |
| room stroke/label `#f3ecff` | room fill (panel) | 13.45 | 4.5 |
| scroll thumb `#b8a6e8` | lightest sky / darkest sky | 4.89 / 8.76 | 3 |
| scroll thumb hover `#ff9f2e` | lightest sky | 5.19 | 3 |
| on-accent `#2b1300` | orange room button (primary gradient) | 6.27 min | 4.5 |

## Feasibility check

1. Clean starting point: `git status --short` shows only ` M plan.md` (the Team lead's file; allowed). HEAD `775c082 TASK-012: night pixel design for all pages`.
2. Referenced objects exist: `university/building.py` (`Rect`, `Space`, `FLOOR_PLANS`, `STAIRS`, `BOTTOM_CENTRE`, `plan_for`, `plan_room_numbers`, `all_plan_rooms`); `campusmap/layout.py:floor_plan`, `label_text_length`; `campusmap/templates/campusmap/map.html` (legend, room list); `schedule/models.py:128` (`reason`), `:147` (`schedule_change_reason_required`); `schedule/templates/schedule/includes/lesson_item.html:19` (`. Причина: {{ item.change.reason }}`); `notifications/sources.py:218` (`body=obj.reason`); `schedule/admin.py:49` (`reason` in `list_display`); CSS map rules at `static/css/base.css:243-335`, `:759`, `:827`, `static/css/theme.css:535-590`; file input rules `base.css:707-716`, `theme.css:212-231,467`; header rules `base.css:396-500`. `BOTTOM_CENTRE` is used only by `university/building.py` and `university/tests/test_building.py`. "Склад"/"Туалеты" appear only in `building.py` and README. `change.reason` is rendered only in `lesson_item.html`.
3. New names are free: `STAIRS_BOTTOM`, `TOILET`, `DOOR_MIN`, `INNER_ROOMS`, `map-hatch`, `.map-defs`, `.map-room-btn`, `.map-room-off`, the D5 tokens, migration `0005_lessonchange_reason_optional` (latest is `0004_lessonchange_updated_at`).
4. Data and migrations: `makemigrations --check --dry-run` clean before. Prototype in a temporary copy of the repository (`$TMPDIR/t013/proj`): `makemigrations` produced exactly the two operations above; a database seeded before the change (copy of the TASK-012 temporary DB) migrated OK; `seed_demo` ran twice; 8 changes, 0 blank reasons, 39 rooms, no plan room missing; a change saved with an empty reason after `full_clean()`; `makemigrations --check` clean after. All 39 plan room numbers stay the same, so no room disappears and no demo data or test loses a room.
5. Tools: Python 3.12 `.venv`, Django 5.2.19, ruff 0.17.4 (the D4 block passes `ruff check` and `ruff format --check` in the copy). No new dependency.
6. Framework capabilities: `CompressedManifestStaticFilesStorage` leaves fragment-only URLs alone: in the copy, `.map-service rect { fill: url(#map-hatch); }` came out of `collectstatic` unchanged. `paint-order`, `scrollbar-width`, `scrollbar-color` and `::-webkit-scrollbar` are CSS features of current browsers (Chromium supports all; Safari uses `::-webkit-scrollbar`). Headless Chromium is the only browser available for the self-check; Safari behaviour is a risk (below).
7. Environment: no new env variables.
8. Verification is runnable on the current tree: `check` (no issues), `makemigrations --check` (no changes), `ruff check .` (passed), `ruff format --check .` (189 files formatted), `python manage.py test --parallel 1`: **Ran 1051 tests, OK** (log `/tmp/claude-501/test-20261118-045027.log`, 2026-11-18 ~15:56 MSK). Prototype run with D4 plans + reason changes in the copy (log `/tmp/claude-501/test-t013-proto-20261118-044726.log`, ~15:47 MSK): the expected failures only — `university.tests.test_building` (import of `BOTTOM_CENTRE`), `test_blank_reason`, `test_blank_reason_violates_constraint`, `test_change_rendering`, `test_change_label_no_space_before_period`, `test_clamped_labels_exactly`, `test_polygon_points_string`. Map page queries (seeded temp DB): student 7, staff 3, same for `/map/` and `/map/room/room-402/`.
9. Conflicts: none. D2 is stricter than "shares a wall" (≥ 24 units, a door). It also fixes 206, 207 and 308, which have 8–16 units of contact today. Rooms are not renumbered and no room is removed.
10. Assumptions / blockers: none.

## Test plan

Test data uses the existing helpers; no test depends on `seed_demo` except the existing seed tests.

### Traceability

| AC | Tests |
|---|---|
| AC1 | `university/tests/test_building.py::FloorPlanTests::test_no_storage` |
| AC2 | `::test_two_staircases_same_place` |
| AC3 | `::test_entrance_only_on_floor_1` |
| AC4 | `::test_wardrobe_and_security_next_to_entrance`, `::test_l_shapes_are_polygons_with_matching_area` (updated) |
| AC5 | `::test_rooms_open_to_corridor`, `::test_other_spaces_open_to_corridor_or_entrance`, `::test_shared_wall_helper` |
| AC6 | `::test_one_toilet_per_floor_in_one_riser` |
| AC7 | existing `test_full_coverage_no_overlap`, `test_room_numbers`, `test_demo_rooms_on_plan`, `test_polygon_vertices_are_part_corners`, `test_all_plan_rooms_sorted`; `campusmap/tests/test_layout.py` (`test_labels_fit_with_padding`, `test_clamped_labels_exactly` updated, `test_coordinates_are_integers`) |
| AC8 | `campusmap/tests/test_views.py::MapPageTests::test_room_opens_its_floor_and_is_highlighted` (updated), `test_highlight_has_accessible_name`; `core/tests/test_css.py::BaseCssTests::test_map_highlight_rule` (updated); `core/tests/test_design.py::ThemeRuleTests::test_map_highlight_not_hue_only` (unchanged, still passes) and `::test_map_highlight_final` (new) |
| AC9 | `core/tests/test_design.py::ThemeRuleTests::test_map_kinds_distinct`; `campusmap/tests/test_views.py::MapPageTests::test_hatch_pattern_defined` |
| AC10 | `campusmap/tests/test_views.py::MapPageTests::test_no_corridor_label` |
| AC11 | `::test_room_list_buttons`, `test_room_not_on_plan_listed` (updated), `test_floor_without_plan` (updated), `test_room_on_plan_by_number` (updated) |
| AC12 | `schedule/tests/test_views.py::ChangeRenderingTests::test_change_rendering` (updated), `ScheduleUiFixTests::test_change_labels_without_reason` (replaces `test_change_label_no_space_before_period`), `::test_staff_week_hides_reason`; `notifications/tests/test_feed.py::LessonChangeSourceTests::test_change_item_has_no_body`; `notifications/tests/test_views.py::FeedViewTests::test_change_reason_not_shown`; `core/tests/test_home.py::HomeStudentTests::test_lessons_card_hides_reason` |
| AC13 | `schedule/tests/test_validation.py::LessonChangeRuleTests::test_blank_reason_allowed` (replaces `test_blank_reason`), `LessonChangeDBConstraintTests::test_blank_reason_saved_in_db` (replaces `test_blank_reason_violates_constraint`); `makemigrations --check` |
| AC14 | `core/tests/test_design.py::ThemeRuleTests::test_file_input_full_width` + visual check |
| AC15 | visual check (numbers in the REPORT) |
| AC16 | `core/tests/test_design.py::ThemeRuleTests::test_scrollbar_rules` |
| AC17 | existing `TokenTests`, `ExternalResourceTests` (one updated) |
| AC18 | `core/tests/test_design.py::ReadmeTests::test_map_section_current` |

### Access matrix

No view, URL or permission changes. The existing access tests stay and must pass: `campusmap/tests/test_views.py::MapAccessTests` (anonymous 302, student 200, staff 200, superuser 200 as today), the schedule access tests and the notifications access tests. New: `campusmap/tests/test_views.py::MapPageTests::test_map_queries_constant` (below).

### New and updated tests

`university/tests/test_building.py` (import `STAIRS_BOTTOM`, `TOILET`, `DOOR_MIN`, `INNER_ROOMS` instead of `BOTTOM_CENTRE`):
- `test_fixed_elements_same_on_every_floor` → rename `test_two_staircases_same_place`: on every floor exactly one space with `parts == (STAIRS,)` and one with `parts == (STAIRS_BOTTOM,)`, both `LANDMARK` "Лестница"; exactly two "Лестница" spaces; no part equals `CORRIDOR`.
- `test_no_storage`: no label "Склад" on any floor.
- `test_entrance_only_on_floor_1`: "Вход" is on floor 1 only, once, `LANDMARK`, parts `(Rect(236, 500, 160, 72),)`, and `_space_wall(entrance, [CORRIDOR]) >= DOOR_MIN`.
- `test_wardrobe_and_security_next_to_entrance`: on floor 1, "Гардероб" and "Охрана" are `SERVICE`, one part each, each with `_space_wall(space, entrance.parts) >= DOOR_MIN`; "Охрана" area ≤ 72×72; "Гардероб" does not touch "Столовая" (`_space_wall == 0`); "Столовая" has one part and no points.
- `test_rooms_open_to_corridor`: every `ROOM` not in `INNER_ROOMS` has `_space_wall(room, [CORRIDOR]) >= DOOR_MIN` (subTest per floor/label); `INNER_ROOMS == {"211"}` and 211 shares ≥ `DOOR_MIN` with 210.
- `test_other_spaces_open_to_corridor_or_entrance`: every `LANDMARK`/`SERVICE` except the two staircases has `max(_space_wall(s, [CORRIDOR]), _space_wall(s, entrance_parts)) >= DOOR_MIN` (entrance parts empty on floors 2–4); the staircases share exactly 72 with the corridor.
- `test_one_toilet_per_floor_in_one_riser`: per floor exactly one space whose label starts with "Туалет"; labels `{1: "Туалет М", 2: "Туалет Ж", 3: "Туалет М", 4: "Туалет Ж"}`; kind `SERVICE`; parts `(TOILET,)`.
- `test_shared_wall_helper`: the four cases in "Functions".
- `test_l_shapes_are_polygons_with_matching_area`: expected set becomes `{(ROOM, "210")}`.
- `test_landmarks_and_services_per_floor`: landmarks `{1: {"Лестница", "Вход", "Столовая"}, 2: {"Лестница", "Деканат"}, 3: {"Лестница", "Библиотека"}, 4: {"Лестница"}}`; services exactly `{1: {"Туалет М", "Кафедра", "Медпункт", "Охрана", "Гардероб"}, 2: {"Туалет Ж", "Кафедра"}, 3: {"Туалет М", "Кафедра"}, 4: {"Туалет Ж", "Кафедра", "Архив"}}`.
- `test_full_coverage_no_overlap`, `test_room_numbers`, `test_demo_rooms_on_plan`, `test_polygon_vertices_are_part_corners`, `test_all_plan_rooms_sorted`, `test_plans_for_floors_1_to_4_only`: unchanged, must pass.

`campusmap/tests/test_layout.py`:
- `test_clamped_labels_exactly`: expected set `{(f, "Лестница") for f in 1..4} | {(1, "Охрана"), (1, "Гардероб")}`. The set dedups the two staircases; add an assertion that each floor has exactly 2 clamped "Лестница" shapes with `text_length == 56`, "Охрана" 56 and "Гардероб" 72.
- `test_polygon_points_string`: use room 210 on floor 2: `points == "236,188 396,188 396,316 316,316 316,412 236,412"` (the canteen is no longer a polygon).
- Others unchanged.

`campusmap/tests/test_views.py`:
- `test_room_opens_its_floor_and_is_highlighted`: the room list link is `<a class="btn map-room-btn map-current" href="/map/room/room-402/" aria-current="location">402</a>`; `content.count("map-current") == 2` stays.
- `test_room_on_plan_by_number`: the list contains `<a class="btn map-room-btn map-current" href="/map/room/room-114/" aria-current="location">114</a></li>` (no "нет на схеме" note after it).
- `test_room_not_on_plan_listed`: `<a class="btn map-room-btn map-current" href="/map/room/room-199/" aria-current="location">199</a> <span class="map-room-off">нет на схеме</span>`.
- `test_floor_without_plan`: `<a class="btn map-room-btn" href="/map/room/room-501/">501</a> <span class="map-room-off">нет на схеме</span>`.
- `test_landmarks_per_floor`: the floor 1 list (with duplicates) is `["Лестница", "Лестница", "Вход", "Столовая"]` in plan order; floors 2 and 4 contain "Лестница" exactly twice.
- New `MapPageTests::test_room_list_buttons`: on `/map/floor/2/` every room link inside `<ul class="map-room-list">` has `class="btn map-room-btn"`; no `aria-current="location"` without a current room.
- New `::test_hatch_pattern_defined`: the page contains `<pattern id="map-hatch"` exactly once and `class="map-defs"`, and the hidden SVG has `aria-hidden="true"`.
- New `::test_no_corridor_label`: in `_svg_part(content)` the number of `<text ` equals the number of `<g class="map-` groups, and "Коридор" is absent.
- New `::test_map_queries_constant`: student, `/map/room/room-402/`; count with the class's rooms equals the count after adding 5 more rooms (`Room.objects.create`) and equals 7.

`schedule/tests/test_validation.py`:
- `test_blank_reason` → `test_blank_reason_allowed`: `save_lesson_change(LessonChange(..., reason=""))` succeeds and the saved row has `reason == ""`.
- `test_blank_reason_violates_constraint` → `test_blank_reason_saved_in_db`: `LessonChange.objects.create(..., reason="")` inside `transaction.atomic()` does not raise.

`schedule/tests/test_views.py`:
- `ChangeRenderingTests::test_change_rendering`: keep the label assertions; replace the loop that expects the reasons with `assertNotIn` for each reason and `assertNotIn("Причина", content)`.
- `ScheduleUiFixTests::test_change_label_no_space_before_period` → `test_change_labels_without_reason`: content contains `<p class="lesson-change">Отменено</p>`, `<p class="lesson-change">Замена аудитории</p>`, `<p class="lesson-change">Замена преподавателя</p>`, a `lesson-change` paragraph starting with "Перенесено на" and ending with `)</p>`, one starting with "Перенесено с" and ending with `пара</p>`; no `Причина`.
- New `::test_staff_week_hides_reason`: the staff group week for the same data has no reason text and still has "Отменено".
- `test_today_page_hides_reason` (new, `TodayView`): a cancelled lesson today shows "Отменено" and not its reason.

`notifications/tests/test_feed.py`:
- New `LessonChangeSourceTests::test_change_item_has_no_body`: the lesson-change item has `body == ""` and its title is unchanged (for example starts with "Отмена занятия:").

`notifications/tests/test_views.py`:
- New `FeedViewTests::test_change_reason_not_shown`: a change with reason "Секретная причина" appears in the feed by title; "Секретная причина" is not in the page.

`core/tests/test_home.py`:
- New `HomeStudentTests::test_lessons_card_hides_reason`: the reasons used in `setUpTestData` ("Ремонт", "Болезнь") do not appear in the home page.

`core/tests/test_css.py`:
- `test_map_highlight_rule`: base.css still has `.map-current .map-room-label`; tokens.css has `--color-map-highlight`, `--color-map-highlight-fill: #ff9f2e` and `--color-map-highlight-text: #2b1300`; the `.map-current .map-room-label` rule (in base.css or theme.css) uses `var(--color-map-highlight-text)`.

`core/tests/test_design.py`:
- `ExternalResourceTests::test_css_has_no_external_urls`: allow fragment URLs: the regex becomes `^url\("?(\.\./|#)`.
- `TokenTests` required names: add the D5 tokens.
- New `ThemeRuleTests::test_map_highlight_final`: a theme rule for `.map-current rect`/`polygon` uses `var(--color-map-highlight-fill)` as fill and `stroke-width` ≥ 4.
- New `::test_map_kinds_distinct`: theme rules: `.map-landmark` shape rule uses `var(--color-map-landmark)`; `.map-service` shape rule uses `url(#map-hatch)` and `var(--color-map-service)`; `.map-service-label` has `paint-order: stroke`; `.map-landmark-label` and `.map-service-label` have different fills.
- New `::test_file_input_full_width`: base.css has a rule for `.form input[type="file"]` with `width: 100%`.
- New `::test_scrollbar_rules`: theme.css contains `scrollbar-width: thin`, `scrollbar-color: var(--color-scroll-thumb)`, `::-webkit-scrollbar-thumb`, `var(--color-scroll-thumb-hover)` and `@media (hover: hover) and (pointer: fine)`; no CSS file contains `scrollbar-width: none`; no scrollbar rule has a non-zero `border-radius`.
- New `ReadmeTests::test_map_section_current`: README "## Map" section contains "Туалет М", "Туалет Ж", "Вход", "две лестницы" or "two staircases" (assert the exact phrase you write), and does not contain "Склад".

### Edge cases

- Room 211 (the inner room) is the only room without a corridor door.
- Floor 1 spaces that open onto the entrance, not the corridor (Охрана, Гардероб).
- A room not on the plan (199, 501) in the button grid.
- A change with an empty reason (allowed now) renders the same as one with a reason.
- Badges at their caps ("50+", "Чат (99+)") in the wide header (visual).

### Settings branches

None. Manifest storage and fragment URLs are covered by the existing `FontTests::test_manifest_rewrites_font_url` (it runs `collectstatic` over the new theme.css).

## Implementation order

1. Plans: replace the data (D4), update `university/tests/test_building.py`, `campusmap/tests/test_layout.py`. Run `python manage.py test university campusmap` (log).
2. Reasons: model, migration, `lesson_item.html`, `notifications/sources.py`, tests. Run `python manage.py test schedule notifications core.tests.test_home` (log).
3. Map look: tokens, hatch defs, styles, legend, room list; update and add tests. Check all floors at 360/1024.
4. File input, wide header, scrollbar. Check visually.
5. README "## Map". Full verification. Visual self-check of every row in "Pages to check visually". REPORT.

## Verification

```bash
source .venv/bin/activate
python manage.py check
DEBUG=false ALLOWED_HOSTS=example.com ADMIN_URL=ci-staff-panel/ SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop python manage.py check --deploy --fail-level WARNING
python manage.py makemigrations --check --dry-run
python manage.py test --parallel 1 2>&1 | tee "$TMPDIR/test-$(date +%Y%m%d-%H%M%S).log"
python scripts/run_tests_at.py 2026-11-19T00:00:00 2>&1 | tee "$TMPDIR/test-midnight-$(date +%Y%m%d-%H%M%S).log"
# Migration on a database seeded BEFORE the change (temporary files only):
#   mkdir -p "$TMPDIR/t013-before" && git archive HEAD | tar -x -C "$TMPDIR/t013-before"
#   (the archive has no .env: run its commands with DEBUG=true SECRET_KEY=<any 50+ char dummy> DEMO_PASSWORD=... PRIVATE_MEDIA_ROOT="$TMPDIR/...")
#   (cd "$TMPDIR/t013-before" && DATABASE_URL="sqlite:///$TMPDIR/t013-before.sqlite3" python manage.py migrate && DATABASE_URL="sqlite:///$TMPDIR/t013-before.sqlite3" python manage.py seed_demo)
#   DATABASE_URL="sqlite:///$TMPDIR/t013-before.sqlite3" python manage.py migrate   # in the project, with your changes
#   DATABASE_URL="sqlite:///$TMPDIR/t013-before.sqlite3" python manage.py seed_demo  # twice
DATABASE_URL="sqlite:///$TMPDIR/t013-fresh.sqlite3" python manage.py migrate && DATABASE_URL="sqlite:///$TMPDIR/t013-fresh.sqlite3" python manage.py seed_demo && DATABASE_URL="sqlite:///$TMPDIR/t013-fresh.sqlite3" python manage.py seed_demo
ruff check <the Python files of this task>
ruff format --check <the Python files of this task>
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
git status --short
```
- `git archive HEAD | tar -x -C <dir>` only reads git; it does not change the index or history. Never run `git stash`, `git checkout` or `git worktree`.
- Set `DEMO_PASSWORD` and `PRIVATE_MEDIA_ROOT="$TMPDIR/…"` for seed runs (role file). Never touch `db.sqlite3`.
- If any test run fails or stalls, even once, put the test name, the Moscow time and the traceback excerpt into the REPORT.

## Risks

- **Test churn.** Only the tests listed above change, each with a `# TASK-013:` reason.
- **Reason-only edits.** `LessonChange.updated_at` is `auto_now`, so a staff edit of only the (now hidden) reason in the admin marks the change unread again in the feed with no visible difference. Rare (admin only); not fixed in this task.
- **Safari scrollbars.** `::-webkit-scrollbar` turns off macOS overlay scrollbars in Safari; with D14 the thumb shows on hover. Only Chromium is checked locally; the Team lead may check Safari.
- **Hatch pattern.** If the hidden defs SVG is removed or set to `display: none`, service spaces lose their fill in some browsers. Test `test_hatch_pattern_defined` keeps it present.
- **Label clamping.** "Охрана" (95%) and "Гардероб" (92%) are slightly compressed by `textLength`; check legibility at 360 px.
