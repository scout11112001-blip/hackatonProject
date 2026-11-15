# TASK-008: room map — schematic building plan, highlight from the schedule

Author: Planner. Status: ready for implementation.
Base commit: `bf09738`. Related specs: `TASK-003.md` (schedule, `Room`), `TASK-007.md` (nav, query-count patterns).

Students and staff open «Карта», switch floors, and see every room of the single fictional building as a labelled shape on an inline SVG plan. A tap on a room in the schedule opens the map on that room's floor with the room number in red.

---

## 1. Goal and acceptance criteria

| ID | Criterion |
|---|---|
| AC1 | New app `campusmap` (no models). Room data and room placement stay in `university`. |
| AC2 | Every room number is `NNN` (exactly 3 digits, first digit 1–9) and the first digit equals `floor`. Enforced by field validators + model constraints (admin shows form errors, never 500) AND by DB check constraints. `floor` is limited to 1–9. All existing and demo rooms comply; the migration applies on seeded data. |
| AC3 | A room's position is a cell of a fixed per-floor grid, stored in `Room.map_cell` (editable in the admin, blank = not on the map). One room per cell per floor (DB unique constraint). A cell taken by a landmark on that floor is rejected (model validation). |
| AC4 | `/map/` shows the lowest floor that has rooms; `/map/floor/<n>/` shows floor `n` (404 if no room is on that floor); floor switcher lists every floor with at least one room, current floor marked. |
| AC5 | Landmarks (not `Room` rows, not linked to the schedule) are drawn from code: «Лестница» on every floor, «Вход» and «Столовая» on floor 1, «Деканат» on floor 2, «Библиотека» on floor 3. A legend explains the shapes. |
| AC6 | `/map/room/<code>/` opens the room's floor with the room's number in red via ONE CSS class `map-current`; the room shape has `aria-current="location"` and an SVG `<title>`. Unknown code → 404. Nothing from the query string is rendered. |
| AC7 | A room without a position is listed with «— нет на схеме»; its highlight URL opens its floor (no SVG highlight, list item marked). |
| AC8 | Schedule pages (student today/week, staff group week): the room of every happening lesson is a link to its highlight URL; the NEW room after a room change/move; cancelled and moved-out lessons keep plain text. No extra queries. |
| AC9 | Nav item «Карта» for students and staff. Any logged-in user may open the map; anonymous → login redirect. No personal data on the map. |
| AC10 | At 360 px the SVG scales to the content width (`viewBox`, no fixed width), no horizontal scroll; room labels ≥ 16 px, landmark labels ≥ 12 px on screen. |
| AC11 | Map page: a fixed number of queries regardless of the number of rooms (one query for rooms); query-count tests for the map and the schedule links. |
| AC12 | `seed_demo` (idempotent) gives all 7 demo rooms a cell. |

## 2. Out of scope
Route finding, several buildings, room occupancy/timetables, search, zoom/pan, JavaScript, clickable rooms inside the SVG, the pixel-art theme, chat (TASK-009), a «Карта» nav item for the superuser (the superuser can open `/map/` directly).

## 3. Design decisions

**D1. App.** New app `campusmap` for the map pages (views, layout geometry, templates). `university` keeps the `Room` data, its validation and the building grid (`university/building.py`), because `Room` validation must know which cells are taken by landmarks and `university` must not import a presentation app. Dependency direction: `campusmap` → `university`; `schedule` templates → `campusmap` URLs only.

**D2. Floor vs number: validate both fields.** `floor` stays a real column (used by ordering, `list_filter`, templates, tests, seeds). Deriving it from the number (a generated column or removing the field) would change every `Room` creation in code and tests and needs a table rebuild with data conversion. Validation:
- field level: `number` RegexValidator `^[1-9][0-9]{2}$`; `floor` 1–9 → field errors in the admin;
- model level: check constraint "number starts with floor" → non-field error. Django skips constraint validation for fields that already failed field validation, so the user sees one message per problem (verified, 9.6).
- DB level: three check constraints (format, floor 1–9, match).
The "match" constraint compares strings (`number LIKE CAST(floor AS text) || '%'`); it never casts user text to an integer, so constraint validation cannot raise a database error on PostgreSQL.

**D3. Positions: a cell of a fixed grid, stored on `Room` (`map_cell`).** Free coordinates would need bounds and overlap checks against rooms and landmarks; a fixed layout keyed by room code would make rooms created in the admin invisible until a code change. A grid cell is editable in the admin as a dropdown, needs one unique constraint (`floor`, `map_cell`) and one landmark check, and keeps all geometry in code, where the UI stage can restyle it.

Grid: two rows of 5 cells along a central corridor. Columns 1–5; top row `N1…N5`, bottom row `S1…S5`. `N1` is the stairs on every floor, so rooms use `N2…N5`, `S1…S5`.
```
 ┌──────┬──────┬──────┬──────┬──────┐
 │ N1   │ N2   │ N3   │ N4   │ N5   │   top row
 ├──────┴──────┴──────┴──────┴──────┤
 │            corridor              │
 ├──────┬──────┬──────┬──────┬──────┤
 │ S1   │ S2   │ S3   │ S4   │ S5   │   bottom row
 └──────┴──────┴──────┴──────┴──────┘
```
Landmarks: `N1` «Лестница» (every floor); floor 1: `S3` «Вход», `S4+S5` «Столовая»; floor 2: `S1+S2` «Деканат»; floor 3: `S4+S5` «Библиотека».

**D4. URLs: path segments, not query strings.** `/map/`, `/map/floor/<int:floor>/`, `/map/room/<slug:code>/`. The URL resolver rejects malformed values (404) before the view runs, nothing is parsed from the query string, and links stay short. A floor that has no rooms (or 0, or 10+) → 404: such a URL is broken (the switcher never produces it); silently showing another floor would hide the error. No floor segment → the lowest floor with rooms.

**D5. Cancelled / moved-out lessons keep plain room text.** The lesson does not take place in that room at that time; a link would send the student to a room where nothing happens. Happening lessons (regular, moved-in, room-changed, teacher-replaced) link to the room where they happen (`item.room`, already the new room).

**D6. Label size.** `viewBox` width 400 user units. Content width at a 360 px screen is 328 px (`.site-main` padding `--space-3` = 16 px each side), scale 0.82. Room labels 20 units → 16.4 px; landmark labels 15 units → 12.3 px (12 px is the smallest size we accept as readable on a phone). All label widths fit their cells (test with 0.6 em per character).

**D7. Highlight colour.** One class `map-current`; colour token `--color-map-highlight: #c00000` (contrast on white ≈ 6.6:1). Two selectors use the class: the SVG label and the room-list link. Easy to restyle in the UI stage.

---

## 4. Architecture

### 4.1 Files
Create:
| File | Content |
|---|---|
| `university/building.py` | `MapCell`, `STAIRS_CELL`, `Landmark`, `LANDMARKS`, `landmarks_on`, `blocked_cells` |
| `university/migrations/0003_room_number_format_and_map_cell.py` | generated: `makemigrations university --name room_number_format_and_map_cell` |
| `university/tests/test_building.py`, `university/tests/test_admin.py` | tests |
| `campusmap/__init__.py`, `campusmap/apps.py` (`CampusmapConfig`, `name = "campusmap"`, `verbose_name = "Карта"`, `default_auto_field = "django.db.models.BigAutoField"`) | app |
| `campusmap/layout.py` | geometry: `Rect`, `MapShape`, `FloorPlan`, `cell_rect`, `span_rect`, `floor_plan` |
| `campusmap/views.py`, `campusmap/urls.py` | `MapView`, 3 routes |
| `campusmap/templates/campusmap/map.html` | page |
| `campusmap/tests/__init__.py`, `campusmap/tests/test_layout.py`, `campusmap/tests/test_views.py` | tests |

Change:
| File | Change |
|---|---|
| `university/models.py` | `Room`: validators, `map_cell`, constraints, `clean()` |
| `university/admin.py` | `RoomAdmin.list_display` += `"map_cell"` |
| `university/tests/test_models.py` | room tests (5.1) |
| `schedule/tests/helpers.py` | `make_room` derives `floor` from the number |
| `schedule/demo.py` | `RoomSeed.map_cell`; rooms saved with `full_clean()` |
| `schedule/templates/schedule/includes/lesson_item.html` | room links |
| `schedule/tests/test_views.py`, `schedule/tests/test_demo.py` | tests |
| `templates/base.html` | nav «Карта» |
| `config/settings.py` | `"campusmap"` in `INSTALLED_APPS` after `"notifications"` |
| `config/urls.py` | `path("", include("campusmap.urls")),` after the notifications include |
| `pyproject.toml` | `"campusmap"` in `known-first-party` |
| `static/css/tokens.css` | `--color-map-highlight: #c00000;` |
| `static/css/base.css` | map rules (4.8) |
| `core/tests/test_css.py` | highlight rule test |
| `README.md` | `## Map` section; Known limitations bullet |

No new dependencies, no env variables, no JavaScript, no image files.

### 4.2 `university/building.py`
```python
"""The fictional building: a fixed grid of map cells and landmarks (one building)."""

from dataclasses import dataclass

from django.db import models

STAIRS_CELL = "N1"


class MapCell(models.TextChoices):
    N2 = "N2", "Верхний ряд, место 2"
    N3 = "N3", "Верхний ряд, место 3"
    N4 = "N4", "Верхний ряд, место 4"
    N5 = "N5", "Верхний ряд, место 5"
    S1 = "S1", "Нижний ряд, место 1"
    S2 = "S2", "Нижний ряд, место 2"
    S3 = "S3", "Нижний ряд, место 3"
    S4 = "S4", "Нижний ряд, место 4"
    S5 = "S5", "Нижний ряд, место 5"


@dataclass(frozen=True)
class Landmark:
    key: str
    label: str
    cells: tuple[str, ...]   # adjacent cells of one row
    floor: int | None        # None = every floor


LANDMARKS: tuple[Landmark, ...] = (
    Landmark("stairs", "Лестница", (STAIRS_CELL,), None),
    Landmark("entrance", "Вход", ("S3",), 1),
    Landmark("canteen", "Столовая", ("S4", "S5"), 1),
    Landmark("deanery", "Деканат", ("S1", "S2"), 2),
    Landmark("library", "Библиотека", ("S4", "S5"), 3),
)


def landmarks_on(floor: int) -> list[Landmark]:
    return [lm for lm in LANDMARKS if lm.floor is None or lm.floor == floor]


def blocked_cells(floor: int) -> dict[str, Landmark]:
    return {cell: lm for lm in landmarks_on(floor) for cell in lm.cells}
```

### 4.3 `university/models.py` — `Room`
- `from university.building import MapCell, blocked_cells` (absolute import, module has no Django model imports → no cycle) and `from django.db.models.functions import Cast`.
- Constants: `ROOM_NUMBER_RE = r"^[1-9][0-9]{2}$"`, `MAX_FLOOR = 9`.
- `floor`: validators `MinValueValidator(1), MaxValueValidator(MAX_FLOOR)` (was 20).
- `number`: keep `max_length=10, unique=True`; add `validators=[RegexValidator(ROOM_NUMBER_RE, "Номер аудитории: ровно три цифры, первая цифра — этаж (1–9).")]`, `help_text="Три цифры, первая — этаж: 205 — аудитория на 2 этаже."`.
- New field after `number`: `map_cell = models.CharField("место на схеме", max_length=2, blank=True, default="", choices=MapCell.choices, help_text="Пусто — аудитории нет на схеме.")`.
- `Meta.constraints` (replace `university_room_floor_1_20`; keep everything else):
```python
models.CheckConstraint(
    condition=models.Q(floor__gte=1) & models.Q(floor__lte=MAX_FLOOR),
    name="university_room_floor_1_9",
),
models.CheckConstraint(
    condition=models.Q(number__regex=ROOM_NUMBER_RE),
    name="university_room_number_nnn",
    violation_error_message="Номер аудитории: ровно три цифры, первая цифра — этаж (1–9).",
),
models.CheckConstraint(
    condition=models.Q(number__startswith=Cast("floor", output_field=models.CharField())),
    name="university_room_floor_matches_number",
    violation_error_message="Этаж должен совпадать с первой цифрой номера аудитории.",
),
models.CheckConstraint(
    condition=models.Q(map_cell__in=["", *MapCell.values]),
    name="university_room_map_cell_value",
),
models.UniqueConstraint(
    fields=["floor", "map_cell"],
    condition=~models.Q(map_cell=""),
    name="university_room_unique_map_cell",
    violation_error_message="Это место на схеме этажа уже занято другой аудиторией.",
),
```
- `clean(self)` (new; after `__str__`):
  1. `super().clean()`.
  2. If `self.map_cell` and `isinstance(self.floor, int)` and `1 <= self.floor <= MAX_FLOOR`: `landmark = blocked_cells(self.floor).get(self.map_cell)`; if found → `raise ValidationError(f"Это место на {self.floor} этаже занято: {landmark.label}.")` (non-field).

### 4.4 Migration
`python manage.py makemigrations university --name room_number_format_and_map_cell` → `university/migrations/0003_room_number_format_and_map_cell.py` with: `AlterField` `floor` and `number` (validators), `AddField` `map_cell`, `RemoveConstraint university_room_floor_1_20`, five `AddConstraint`. Do not edit it by hand. It must apply on a database seeded with the current code (checked, 9.4).

### 4.5 `campusmap/layout.py`
All values are `int` (Django localizes floats with a comma under `ru`, which breaks SVG attributes). Use `//` for halves.
```python
VIEWBOX_WIDTH = 400
VIEWBOX_HEIGHT = 240
ROOM_LABEL_SIZE = 20       # user units, see D6
LANDMARK_LABEL_SIZE = 15
CELL_WIDTH = 72
CELL_HEIGHT = 80
COLUMN_X = {1: 12, 2: 88, 3: 164, 4: 240, 5: 316}
ROW_Y = {"N": 12, "S": 148}
OUTLINE = Rect(4, 4, 392, 232)
CORRIDOR = Rect(12, 96, 376, 48)


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def cx(self) -> int: return self.x + self.width // 2
    @property
    def cy(self) -> int: return self.y + self.height // 2


@dataclass(frozen=True)
class MapShape:
    kind: str            # "room" | "landmark"
    label: str           # room number or landmark label
    rect: Rect
    is_current: bool = False


@dataclass(frozen=True)
class FloorPlan:
    floor: int
    width: int
    height: int
    outline: Rect
    corridor: Rect
    shapes: list[MapShape]
```
(Define `Rect` before the constants that use it.)

**`cell_rect(cell: str) -> Rect`** — `row, col = cell[0], int(cell[1:])`; `Rect(COLUMN_X[col], ROW_Y[row], CELL_WIDTH, CELL_HEIGHT)`. `KeyError`/`ValueError` for an unknown cell (callers pass only `STAIRS_CELL` and `MapCell` values).

**`span_rect(cells: Sequence[str]) -> Rect`** — union of `cell_rect` of adjacent cells in one row: `x = min(x)`, `y` of the row, `width = max(x + width) - min(x)`, `height = CELL_HEIGHT`.

**`floor_plan(floor: int, rooms: Sequence[Room], current: Room | None) -> FloorPlan`**
1. `blocked = blocked_cells(floor)`.
2. Landmark shapes: `[MapShape("landmark", lm.label, span_rect(lm.cells)) for lm in landmarks_on(floor)]`.
3. Room shapes: for each `room` in `rooms` with `room.floor == floor`, `room.map_cell` non-empty and `room.map_cell not in blocked`: `MapShape("room", room.number, cell_rect(room.map_cell), is_current=current is not None and room.pk == current.pk)`. Keep the input order.
4. Return `FloorPlan(floor, VIEWBOX_WIDTH, VIEWBOX_HEIGHT, OUTLINE, CORRIDOR, landmark_shapes + room_shapes)`.
No queries (works on the given list).

### 4.6 Views and URLs
`campusmap/urls.py`:
```python
app_name = "campusmap"
urlpatterns = [
    path("map/", views.MapView.as_view(), name="map"),
    path("map/floor/<int:floor>/", views.MapView.as_view(), name="floor"),
    path("map/room/<slug:code>/", views.MapView.as_view(), name="room"),
]
```
`campusmap/views.py` — `MapView(TemplateView)`, `template_name = "campusmap/map.html"`, `http_method_names = ["get"]`. No role mixin (any logged-in user; `LoginRequiredMiddleware` handles anonymous).

Dataclasses in `views.py`:
```python
@dataclass(frozen=True)
class RoomEntry:
    number: str
    url: str
    on_map: bool
    is_current: bool

@dataclass(frozen=True)
class FloorEntry:
    number: int
    url: str
    is_current: bool
    rooms: list[RoomEntry]
```
`get_context_data(**kwargs)`:
1. `rooms = list(Room.objects.order_by("floor", "number"))` — the only query of the view.
2. `floors = sorted({r.floor for r in rooms})`.
3. `code = self.kwargs.get("code")`; `floor = self.kwargs.get("floor")`; `current = None`.
   - If `code is not None`: `current = next((r for r in rooms if r.code == code), None)`; `None` → `raise Http404`; `floor = current.floor`.
   - Elif `floor is not None`: `floor not in floors` → `raise Http404`.
   - Else: `floor = floors[0] if floors else None`.
4. `plan = floor_plan(floor, rooms, current) if floor is not None else None`.
5. Room list: for each floor `f` in `floors`: `FloorEntry(f, reverse("campusmap:floor", args=[f]), f == floor, [RoomEntry(r.number, reverse("campusmap:room", args=[r.code]), bool(r.map_cell) and r.map_cell not in blocked_cells(f), current is not None and r.pk == current.pk) for r in rooms if r.floor == f])`.
6. Context: `plan`, `floors` (the `FloorEntry` list), `current`.

### 4.7 Templates
`campusmap/map.html` (extends `base.html`, title «Карта»):
```django
<h1>Карта</h1>
{% if not floors %}
  <p>Аудиторий пока нет.</p>
{% else %}
  <nav class="floor-switcher" aria-label="Этажи">
    <span>Этаж:</span>
    <ul>
      {% for f in floors %}
      <li><a href="{{ f.url }}"{% if f.is_current %} class="floor-current" aria-current="page"{% endif %}>{{ f.number }}</a></li>
      {% endfor %}
    </ul>
  </nav>
  <svg class="map-svg" viewBox="0 0 {{ plan.width }} {{ plan.height }}" role="img" aria-labelledby="map-title">
    <title id="map-title">Схема, {{ plan.floor }} этаж</title>
    <rect class="map-outline" x="{{ plan.outline.x }}" y="{{ plan.outline.y }}" width="{{ plan.outline.width }}" height="{{ plan.outline.height }}"/>
    <rect class="map-corridor" x="{{ plan.corridor.x }}" y="{{ plan.corridor.y }}" width="{{ plan.corridor.width }}" height="{{ plan.corridor.height }}"/>
    {% for s in plan.shapes %}
    <g class="map-{{ s.kind }}{% if s.is_current %} map-current{% endif %}"{% if s.is_current %} aria-current="location"{% endif %}>
      <title>{% if s.kind == "room" %}Аудитория {{ s.label }}{% else %}{{ s.label }}{% endif %}</title>
      <rect x="{{ s.rect.x }}" y="{{ s.rect.y }}" width="{{ s.rect.width }}" height="{{ s.rect.height }}"/>
      <text class="map-{{ s.kind }}-label" x="{{ s.rect.cx }}" y="{{ s.rect.cy }}" text-anchor="middle" dominant-baseline="central">{{ s.label }}</text>
    </g>
    {% endfor %}
  </svg>
  <ul class="map-legend">
    <li><svg class="map-legend-swatch" viewBox="0 0 24 16" aria-hidden="true"><g class="map-room"><rect x="1" y="1" width="22" height="14"/></g></svg> Аудитория</li>
    <li><svg class="map-legend-swatch" viewBox="0 0 24 16" aria-hidden="true"><g class="map-landmark"><rect x="1" y="1" width="22" height="14"/></g></svg> Вход, лестница, деканат, библиотека, столовая</li>
  </ul>
  <h2>Все аудитории</h2>
  {% for f in floors %}
  <h3>{{ f.number }} этаж</h3>
  <ul class="map-room-list">
    {% for r in f.rooms %}
    <li><a href="{{ r.url }}"{% if r.is_current %} class="map-current" aria-current="location"{% endif %}>{{ r.number }}</a>{% if not r.on_map %} — нет на схеме{% endif %}</li>
    {% endfor %}
  </ul>
  {% endfor %}
{% endif %}
```
No `width`/`height` attributes on `.map-svg`. Nothing above the map mentions the highlighted room.

`schedule/templates/schedule/includes/lesson_item.html`, the `lesson-room` paragraph becomes:
```django
<p class="lesson-room">Аудитория:
  {% if item.original_room %}<del class="room" data-room-code="{{ item.original_room.code }}">{{ item.original_room.number }}, {{ item.original_room.floor }} этаж</del>
  <ins>{% if item.is_happening %}<a class="room" data-room-code="{{ item.room.code }}" href="{% url 'campusmap:room' item.room.code %}">{{ item.room.number }}, {{ item.room.floor }} этаж</a>{% else %}<span class="room" data-room-code="{{ item.room.code }}">{{ item.room.number }}, {{ item.room.floor }} этаж</span>{% endif %}</ins>
  {% elif item.is_happening %}<a class="room" data-room-code="{{ item.room.code }}" href="{% url 'campusmap:room' item.room.code %}">{{ item.room.number }}, {{ item.room.floor }} этаж</a>
  {% else %}<span class="room" data-room-code="{{ item.room.code }}">{{ item.room.number }}, {{ item.room.floor }} этаж</span>{% endif %}
</p>
```
`item.room` is already loaded by `schedule/services.py` (the template already renders `item.room.code`), so the links add no queries. The deleted original room is never a link.

`templates/base.html`: student branch, after «Расписание»: `<li><a href="{% url 'campusmap:map' %}">Карта</a></li>`; staff branch, after «Расписание»: the same item.

### 4.8 CSS
`static/css/tokens.css`: add `--color-map-highlight: #c00000;` to the existing `:root` block.
`static/css/base.css` append:
```css
.map-svg {
  display: block;
  width: 100%;
  height: auto;
  margin: var(--space-2) 0;
}

.map-outline,
.map-room rect,
.map-landmark rect,
.map-corridor {
  fill: none;
  stroke: var(--color-text);
  stroke-width: 2;
}

.map-corridor {
  stroke: var(--color-border);
}

.map-landmark rect {
  stroke: var(--color-muted);
  stroke-dasharray: 6 4;
}

.map-room-label {
  font-size: 20px;
  fill: var(--color-text);
}

.map-landmark-label {
  font-size: 15px;
  fill: var(--color-muted);
}

/* Highlighted room: one class, restyle in the UI stage. */
.map-current .map-room-label {
  fill: var(--color-map-highlight);
}

a.map-current {
  color: var(--color-map-highlight);
}

.floor-switcher ul,
.map-legend,
.map-room-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.floor-switcher ul {
  display: inline-flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.floor-switcher a {
  display: inline-block;
  min-width: 2.75rem;
  min-height: 2.75rem;
  line-height: 2.75rem;
  text-align: center;
}

.floor-current {
  font-weight: bold;
}

.map-legend-swatch {
  width: 1.5rem;
  height: 1rem;
  vertical-align: middle;
}
```
(SVG `font-size` in px inside a `viewBox` is in user units and scales with the drawing.)

### 4.9 Seed — `schedule/demo.py`
- `RoomSeed` gets `map_cell: str`. Values: `room-101` N2, `room-114` N4, `room-205` N3, `room-212` S4, `room-308` N2, `room-315` N5, `room-402` N3 (none on a landmark cell; checked against D3).
- Replace the `update_or_create` loop:
```python
room = Room.objects.filter(code=seed.code).first() or Room(code=seed.code)
room.floor, room.number, room.map_cell = seed.floor, seed.number, seed.map_cell
room.full_clean()
room.save()
rooms[seed.code] = room
```
A conflict with an admin-made room (same number or cell) raises `ValidationError`, which `seed_demo` already turns into «Demo data conflicts with existing data: …» (no traceback). Summary line unchanged.

### 4.10 Test helper — `schedule/tests/helpers.py`
`make_room(code: str, floor: int | None = None) -> Room`: `number = code.removeprefix("room-")`; `if floor is None: floor = int(number[0])`. This makes the existing calls `make_room("room-202")`, `make_room("room-303")`, `make_room("room-700")` valid (they used floor 1 by default). Calls with an explicit consistent floor (`room-205`, 2; `room-999`, 9) are unchanged.

### 4.11 README
- `## Map` (after `## Notifications`): URLs, grid and landmarks (D3), how to place a room in the admin («Место на схеме»), room-number rule (NNN, first digit = floor), highlight class `map-current`.
- Known limitations: «The map has one building and a fixed grid of 9 room places per floor; landmarks are defined in code (`university/building.py`).»

---

## 5. Functions and their tests (summary)
| Function | Tests |
|---|---|
| `building.landmarks_on`, `blocked_cells` | `university/tests/test_building.py::BuildingTests` |
| `Room` validators, constraints, `clean` | `university/tests/test_models.py::RoomNumberTests`, `RoomMapCellTests`; `university/tests/test_admin.py::RoomAdminTests` |
| `layout.cell_rect`, `span_rect`, `floor_plan` | `campusmap/tests/test_layout.py::LayoutTests` |
| `MapView` | `campusmap/tests/test_views.py::*` |
| `lesson_item.html` links | `schedule/tests/test_views.py::RoomLinkTests` |
| seed rooms | `schedule/tests/test_demo.py` (new methods) |

---

## 6. Test plan

### 6.0 Rules
- Test data via helpers (`schedule/tests/helpers.py`, `accounts/tests/helpers.py`); rooms via `make_room` or `Room(...)` + `full_clean()`; never seed data except in `test_demo.py`.
- View tests that touch the schedule use `FrozenClockMixin` (default `frozen_now` is fine; the lesson dates must match it). Map tests are clock-independent (no `FrozenClockMixin` needed).
- Save full test output to files; report every failed run by test name, Moscow time and traceback excerpt.

### 6.1 Traceability
| AC | Tests |
|---|---|
| AC1 | `campusmap/tests/test_views.py::MapViewTests::*`; `makemigrations --check` |
| AC2 | `university/tests/test_models.py::RoomNumberTests::*`, `university/tests/test_admin.py::RoomAdminTests::test_mismatch_shows_error`, `test_bad_number_shows_field_error`; `schedule/tests/test_demo.py::…::test_demo_rooms_valid_and_placed` |
| AC3 | `RoomMapCellTests::*`, `RoomAdminTests::test_landmark_cell_shows_error`, `test_valid_room_saved` |
| AC4 | `MapViewTests::test_default_floor_is_lowest`, `test_switcher_lists_only_floors_with_rooms`, `test_current_floor_marked`, `test_floor_without_rooms_404`, `test_non_numeric_floor_404` |
| AC5 | `BuildingTests::*`, `MapViewTests::test_landmarks_per_floor`, `test_legend_present` |
| AC6 | `MapViewTests::test_room_opens_its_floor_and_is_highlighted`, `test_highlight_has_accessible_name`, `test_unknown_room_404`, `test_query_string_not_rendered`, `core/tests/test_css.py::…::test_map_highlight_rule` |
| AC7 | `MapViewTests::test_room_without_cell_listed_and_floor_opens` |
| AC8 | `schedule/tests/test_views.py::RoomLinkTests::*` |
| AC9 | `MapAccessTests::*`, `MapNavTests::*`, `MapViewTests::test_no_personal_data` |
| AC10 | `MapViewTests::test_svg_scales`, `LayoutTests::test_labels_fit`, `test_label_sizes` |
| AC11 | `MapQueryTests::*`, `RoomLinkTests::test_week_query_count_unchanged_by_links` |
| AC12 | `schedule/tests/test_demo.py::…::test_demo_rooms_valid_and_placed`, `test_seed_twice_keeps_cells` |

### 6.2 Access matrix (`campusmap/tests/test_views.py::MapAccessTests`)
The map has no owner and no personal data, so "own / another student's data" and "own / other faculty" do not apply; every logged-in role gets the same page.
| Actor | `/map/` | `/map/floor/2/` | `/map/room/room-205/` | Test |
|---|---|---|---|---|
| anonymous | 302 `/login/?next=…` | 302 | 302 | `test_anonymous_redirected` (all three URLs) |
| student | 200 | 200 | 200 | `test_student_ok` |
| student without profile | 200 | 200 | 200 | `test_student_without_profile_ok` |
| staff | 200 | 200 | 200 | `test_staff_ok` |
| superuser | 200 | 200 | 200 | `test_superuser_ok` |
| student POST `/map/` | 405 | | | `test_post_not_allowed` |

### 6.3 Behaviour and edge cases
`university/tests/test_models.py`:
- `RoomNumberTests`:
  - `test_valid_numbers` («101» floor 1, «999» floor 9 pass `full_clean`)
  - `test_bad_number_is_field_error` (for «15», «1015», «a05», «012», «2a5», «20 5»: `"number" in message_dict`; the mismatch message is NOT in `message_dict.get("__all__", [])`)
  - `test_floor_out_of_range_is_field_error` (0 and 10 → `"floor"` error)
  - `test_floor_must_match_first_digit` («205» floor 3 → `__all__` == ["Этаж должен совпадать с первой цифрой номера аудитории."])
  - `test_db_rejects_bad_number`, `test_db_rejects_mismatch`, `test_db_rejects_floor_10` (`objects.create` inside `transaction.atomic()` → `IntegrityError`)
- `RoomMapCellTests`:
  - `test_landmark_cell_rejected` (floor 1, `S3` → `__all__` message contains «Вход»; floor 2, `S1` → «Деканат»; floor 3, `S5` → «Библиотека»)
  - `test_same_landmark_cell_free_on_other_floor` (floor 4, `S3` passes)
  - `test_same_cell_same_floor_rejected` (`full_clean` message «Это место на схеме этажа уже занято…»; DB `IntegrityError`)
  - `test_same_cell_other_floor_ok`, `test_many_rooms_without_cell_ok`
  - `test_db_rejects_unknown_cell` (`map_cell="N1"` via `objects.create` → `IntegrityError`; `N1` is not a choice)
- Existing `test_room_code_validator`: change numbers to «199»/«198» with floor 1 (the test checks the code validator only). Existing `test_room_floor_out_of_range_rejected` keeps passing (floor 0, «000»).

`university/tests/test_building.py::BuildingTests`: `test_stairs_on_every_floor` (1–9), `test_floor_landmarks` (exact keys per floor 1, 2, 3, 4), `test_blocked_cells` (floor 1 → {N1, S3, S4, S5}), `test_choices_exclude_stairs`, `test_landmark_cells_adjacent_same_row`.

`university/tests/test_admin.py::RoomAdminTests` (superuser client, `admin:university_room_add`): `test_valid_room_saved` (302), `test_bad_number_shows_field_error` (200, message), `test_mismatch_shows_error` (200, mismatch message), `test_landmark_cell_shows_error` (200, «занято: Вход»), `test_duplicate_cell_shows_error` (200).

`campusmap/tests/test_layout.py::LayoutTests`:
- `test_cells_inside_viewbox_and_disjoint` (all `MapCell` values + `STAIRS_CELL` and every landmark `span_rect`: inside `OUTLINE`; room cells pairwise disjoint; none overlaps `CORRIDOR`)
- `test_coordinates_are_integers` (every `Rect` field and `cx`/`cy` is `int`)
- `test_labels_fit` (`3 * 0.6 * ROOM_LABEL_SIZE <= CELL_WIDTH`; for every landmark `len(label) * 0.6 * LANDMARK_LABEL_SIZE <= span width`)
- `test_label_sizes` (`ROOM_LABEL_SIZE * 328 / VIEWBOX_WIDTH >= 16`, `LANDMARK_LABEL_SIZE * 328 / VIEWBOX_WIDTH >= 12`)
- `test_floor_plan_marks_current` (exactly one shape `is_current`)
- `test_room_without_cell_not_drawn`, `test_room_on_blocked_cell_not_drawn` (built with `Room(...)` objects in memory, no save), `test_other_floor_rooms_not_drawn`

`campusmap/tests/test_views.py` (rooms: `101` N2, `114` none, `205` N3, `402` N3 unless stated):
- `MapViewTests`:
  - `test_default_floor_is_lowest` (`/map/` → `<title id="map-title">Схема, 1 этаж</title>`)
  - `test_switcher_lists_only_floors_with_rooms` (floors 1, 2, 4 linked; no `/map/floor/3/` link)
  - `test_current_floor_marked` (`aria-current="page"` exactly once, on floor 2 for `/map/floor/2/`)
  - `test_floor_without_rooms_404` (`/map/floor/3/`, `/map/floor/0/`, `/map/floor/10/`)
  - `test_non_numeric_floor_404` (`/map/floor/abc/`, `/map/floor/-1/`)
  - `test_room_opens_its_floor_and_is_highlighted` (`/map/room/room-402/` → floor 4 title; exactly one `map-current` inside the `<svg class="map-svg"` … `</svg>` part; the list link of 402 has `class="map-current"`; no other room has it)
  - `test_highlight_has_accessible_name` (`aria-current="location"` on the group and `<title>Аудитория 402</title>`)
  - `test_unknown_room_404` (`/map/room/room-404/`, `/map/room/ROOM-101/`)
  - `test_room_without_cell_listed_and_floor_opens` («114</a> — нет на схеме» in the list; `/map/room/room-114/` → 200, floor 1, no `map-current` inside the SVG, list link marked)
  - `test_landmarks_per_floor` (floor 1: «Вход», «Столовая», «Лестница»; floor 2: «Деканат»; floor 4: «Лестница» only of the landmark labels)
  - `test_legend_present`, `test_room_list_grouped_by_floor` (h3 «1 этаж», «2 этаж», «4 этаж»; each room links to `/map/room/<code>/`)
  - `test_no_rooms_empty_state` («Аудиторий пока нет.»)
  - `test_query_string_not_rendered` (`/map/?floor=<script>x</script>&room=room-205` → 200, floor 1 shown, `<script>x` and `room-205` highlight absent)
  - `test_svg_scales` (`viewBox="0 0 400 240"`; the `<svg class="map-svg" …>` start tag has no ` width=` / ` height=`)
  - `test_no_personal_data` (create a student; his last name and username do not appear on `/map/`)
- `MapQueryTests`: `test_queries_constant` (staff: count with 4 rooms == count with 20 rooms (floors 1–9, numbers valid); ≤ 4), `test_highlight_view_same_queries` (`/map/room/…` count == `/map/` count)
- `MapNavTests`: `test_student_nav_has_map`, `test_staff_nav_has_map` (`href="/map/"` on `/profile/`), `test_superuser_nav_has_no_map`

`schedule/tests/test_views.py::RoomLinkTests(FrozenClockMixin, TestCase)` (lessons in the frozen week; reuse the class setup pattern of `ChangeRenderingTests`):
- `test_regular_lesson_room_links_to_map` (`href="/map/room/room-101/"`, `data-room-code="room-101"` kept)
- `test_cancelled_lesson_room_not_linked`, `test_moved_out_lesson_room_not_linked`
- `test_room_changed_links_new_room_only` (link to the new room; old room inside `<del>` without `href`)
- `test_moved_in_with_new_room_links_new_room`
- `test_today_page_has_links`, `test_staff_group_week_has_links`
- `test_week_query_count_unchanged_by_links` (week with 1 lesson vs 6 lessons → equal counts)
- Existing `test_room_code_attribute` and `test_week_view_query_count_constant` must keep passing.

`schedule/tests/test_demo.py` (existing seed test class, add methods): `test_demo_rooms_valid_and_placed` (7 rooms: `full_clean()` passes, `map_cell` non-empty, no cell blocked on its floor), `test_seed_twice_keeps_cells`.

`core/tests/test_css.py::BaseCssTests::test_map_highlight_rule` (`base.css` contains `.map-current .map-room-label` with `var(--color-map-highlight)`; `tokens.css` defines `--color-map-highlight`).

### 6.4 Settings branches
None (no settings differ by DEBUG). `check --deploy` stays clean.

### 6.5 Query count
`MapQueryTests` (map) and `RoomLinkTests::test_week_query_count_unchanged_by_links` (schedule). Map view for staff: session + user + rooms = 3.

### 6.6 Regression
No bug fix. Existing tests that create rooms keep passing through the `make_room` change (4.10).

---

## 7. Implementation order
1. `university/building.py`, `Room` changes, migration 0003, `make_room` helper; university tests. Full suite green.
2. `campusmap` app skeleton, settings, URLs, `pyproject.toml`; `layout.py` + `test_layout.py`.
3. View, template, CSS, nav + `campusmap/tests/test_views.py`, CSS test.
4. Schedule template links + `RoomLinkTests`.
5. Seed + seed tests; admin `list_display`; README.
6. `ruff format` on changed/new Python files only (not migrations); section 8; `REPORT` to the Reviewer. Do not commit.

## 8. Verification
```bash
source .venv/bin/activate
export DEBUG=true
TS=$(TZ=Europe/Moscow date +%Y%m%d-%H%M%S)
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test 2>&1 | tee "$TMPDIR/test-$TS.log"
python scripts/run_tests_at.py 2026-11-17T23:59:59 2>&1 | tee "$TMPDIR/test-$TS-at-2359.log"
python scripts/run_tests_at.py 2026-11-18T00:00:00 2>&1 | tee "$TMPDIR/test-$TS-at-0000.log"
DEBUG=false SECRET_KEY=ci-dummy-secret-key-not-for-production-0123456789abcdefghijklmnop \
  ALLOWED_HOSTS=example.com ADMIN_URL=staff-panel/ \
  python manage.py check --deploy --fail-level WARNING
ruff check . && ruff format --check .
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
export DATABASE_URL="sqlite:///$TMPDIR/task008.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task008-private" DEMO_PASSWORD='Local-Demo-Pass-2026!'
rm -f "$TMPDIR/task008.sqlite3"
python manage.py migrate && python manage.py seed_demo && python manage.py seed_demo
# Migration on data seeded before the change
python manage.py migrate university 0002 && python manage.py migrate
python manage.py shell -c "from university.models import Room; [r.full_clean() for r in Room.objects.all()]; print(sorted(Room.objects.values_list('number', 'floor', 'map_cell')))"
git status --short
```
Note: `migrate university 0002` reverses 0003 (drops `map_cell` and the new constraints), then `migrate` re-applies it on the seeded rows.
`REPORT`: output tails, test count (was 748), log file names, any failed run by test name and Moscow time, `git status`.

## 9. Feasibility check (2026-11-15 16:32 MSK on `bf09738`)
1. Clean start — `git status --short` → only ` M plan.md`. OK.
2. Referenced objects — `university.Room` (`code` with `RegexValidator`, `floor` 1–20 with constraint `university_room_floor_1_20`, `number` max_length 10 unique; `university/models.py:69-95`); `RoomAdmin` (`university/admin.py`, no explicit `fields`); `ScheduleItem.room`, `original_room`, `is_happening` (`schedule/services.py:25-50`; `original_room` is set for room changes and for moves with a new room, line 215); `lesson_item.html` (renders `item.room.code` already; included by `week_days.html:7` and `today.html:12`, so student today/week and staff group week share it); `schedule/demo.py` `RoomSeed`, `ROOM_SEEDS` (7 rooms, numbers comply), room loop with `update_or_create` (lines 252-256); `make_room` (`schedule/tests/helpers.py:21-23`, floor default 1); room creations in tests: `make_room("room-202")` (`academics/tests/test_views.py:321`), `("room-303")` (`:385`), `("room-700")` (`schedule/tests/test_locking.py:104`), `f"room-{100 + n}"` (`notifications/tests/test_views.py:674`, n ≤ 5), `("room-999", floor=9)`, `("room-205", floor=2)`; direct `Room(...)` only in `university/tests/test_models.py:40-49`; no test asserts a room's floor except `schedule/tests/test_demo.py:44` (distinct floors ≥ 3, still true); existing room markup test `test_room_code_attribute` (`schedule/tests/test_views.py:162-165`); nav in `templates/base.html:18-40`; `.site-main` padding `--space-3` (`base.css`), global `svg { max-width: 100%; height: auto; }`. OK.
3. No collisions — no `campusmap` package, no `university/building.py`, no URL `map/`, no field `map_cell`, no CSS classes `map-*` / `floor-switcher`, no token `--color-map-highlight`. Latest university migration `0002_discipline_room_teacher`. OK.
4. Migrations — `makemigrations --check --dry-run` → «No changes detected». Prototype on a temporary copy of `HEAD` with the 4.3 model: generated migration 0003 (remove `floor_1_20`, add `map_cell`, 4 constraints); applied on a DB seeded with the CURRENT code → OK, rooms `101/1, 114/1, 205/2, 212/2, 308/3, 315/3, 402/4` kept. The local `db.sqlite3` rooms (read only) are the same 7 compliant rooms. OK.
5. Tools — Python 3.12, Django 5.2.19, ruff 0.17.4. OK.
6. Framework — on the temporary copy (SQLite, Django 5.2.19): `CHECK ("number" REGEXP '^[1-9][0-9]{2}$')` is created and enforced (`2a5`, `15` → `IntegrityError`); the match constraint compiles to `"number" LIKE REPLACE(…CAST("floor" AS text)…) || '%'` and rejects `205`/floor 3; `full_clean` reports the constraint `violation_error_message` as `__all__`; the conditional `UniqueConstraint` (`floor`, `map_cell`) is validated by `full_clean` («Это место…»). With an invalid number and no field validator both constraint messages appear (`abc`); hence the field `RegexValidator` (failed fields are excluded from constraint validation). Django renders floats with a comma under `ru` → integer geometry. `<int:…>`, `<slug:…>` converters; `View.http_method_names`. OK.
7. Environment — no new env variables. OK.
8. Verification runnable — current tree: all commands pass (9a); one stalled run, not reproduced (9a).
9. Conflicts — none. Note: `floor` max changes 20 → 9; no existing data or code uses floors above 9 (only `room-999`, floor 9).
10. Assumptions / blockers — none.

### 9a. Verification results on the current tree
- `check` → no issues; `makemigrations --check --dry-run` → «No changes detected».
- `test` → `Ran 748 tests … OK` (`$TMPDIR/test-20261115-163235-t008-feas.log`).
- **Failed run (stall):** `run_tests_at.py 2026-11-17T23:59:59` started 2026-11-15 16:34 MSK stopped printing at 16:36:40 MSK and was killed by the 20-minute limit at about 16:52 MSK (`$TMPDIR/test-20261115-163235-t008-feas-at-2359.log`, no traceback, no `E`/`F`). By the progress count after the last log line, the test running at the stall was `schedule.tests.test_demo.ScheduleDemoTests.test_seeded_schedule_has_no_conflicts` (±1 test: the previous one is `test_rerun_months_later_refreshes_changes`). Re-runs: the full suite at 23:59:59 with a traceback-dump watchdog (17:00 MSK) → 748 OK in 120 s; `schedule.tests.test_demo` + `test_demo_marker` six times → 13 OK each in about 27 s (one run took 96 s wall time with 27.6 s inside tests, so the extra time was outside the test code); full suite at 23:59:59 again (17:13 MSK) → 748 OK. Not reproduced; reported to the Team lead.
- `run_tests_at.py 2026-11-18T00:00:00` → 748 OK (`$TMPDIR/test-20261115-171049-t008-feas-at-0000.log`).
- `check --deploy --fail-level WARNING` → no issues (1 silenced); `ruff check .` → all passed; `ruff format --check .` → 149 files already formatted; CI YAML ok.
- `seed_demo` twice on a temporary DB and PRIVATE_MEDIA_ROOT → OK (second run «Notifications ready: 0 announcements.»).

## 10. Risks
- **Migration on real data**: a non-compliant room would make 0003 fail with `IntegrityError`; the server DB is fresh, local data checked. Fix such rows in the admin before migrating.
- **PostgreSQL**: the regex constraint uses `~` there; the match constraint uses `LIKE` on a cast integer → text, never text → integer, so validation cannot raise a DB error.
- **SQLite REGEXP**: the constraint calls the `REGEXP` function that Django registers on each connection; inserting rows with the plain `sqlite3` CLI fails. Use Django only.
- **Schedule regressions**: links change markup inside `lesson-room`; existing tests on `data-room-code` and query counts guard it.
- **Admin placement races**: two admins choosing the same cell at the same time → the unique constraint rejects the second save (IntegrityError → 500 in the rare race; accepted for the prototype).
