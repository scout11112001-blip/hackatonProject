# TASK-010: room map v2 — realistic portrait floor plans

Author: Planner. Status: ready for implementation.
Base commit: `08671f6`. Related specs: `TASK-008.md` (map, D2 number rule, D6 label size, D7 highlight), `TASK-008-FIX.md` (label fitting, page-assertion rule).

Each of floors 1–4 gets its own fixed plan in code: a vertical corridor in the middle, rooms of different sizes on both sides, one L-shaped space per floor 1 and 2, service spaces, and no free space except the corridor. A room appears on the plan when its number is a plan slot on its floor. `Room.map_cell` is removed.

---

## 1. Acceptance criteria
| ID | Criterion |
|---|---|
| AC1 | `university/building.py` defines `FLOOR_PLANS` for floors 1–4 (data in 4.2). Outline, corridor, stairs (top of the corridor axis) and the bottom-centre space position are the same on every floor; the rest differs per floor. |
| AC2 | On every floor the spaces (all their rectangle parts) lie inside the outline, do not touch the corridor's interior, do not overlap each other, and their total area equals outline area − corridor area. Proven by a test on integer geometry. |
| AC3 | 39 rooms in total (9 / 10 / 10 / 10), numbers NNN with first digit = floor, unique; the demo rooms 101, 114, 205, 212, 308, 315, 402 are on the plan. Two L-shaped spaces (floor 1 «Столовая», floor 2 room 210) are drawn as SVG `<polygon>`; their polygon area equals the sum of their parts. |
| AC4 | Non-teaching spaces: landmarks «Лестница» (every floor), «Вход» (1), «Столовая» (1), «Деканат» (2), «Библиотека» (3); service spaces «Гардероб», «Туалеты» (every floor), «Кафедра», «Медпункт», «Склад», «Охрана», «Архив». Legend explains room / landmark / service. |
| AC5 | Portrait layout: `viewBox` 400 × 648, corridor vertical; room label size stays 20 units (≥ 16 px at 360 px); every label fits its label rectangle with the TASK-008-FIX padding (clamped with `textLength` only where needed). No horizontal scroll at 360 px. |
| AC6 | Linking by number (D1): a room is on the plan when `room.number` is a room slot of `room.floor`'s plan. `Room.map_cell` (field, two constraints, `clean()` check, admin column) is removed by migration `university/0004_remove_room_map_cell`, which applies on a database seeded before the change. Rooms not on the plan (or floors 5–9 without a plan) show «— нет на схеме» and never break the page. |
| AC7 | `seed_demo` (idempotent) creates/updates a `Room` row for every plan room with code `room-<number>`; the 7 demo rooms keep their codes. |
| AC8 | Unchanged: floor switcher (floors that have rooms), highlight URL opens the room's floor with its number in red (`map-current`, `aria-current="location"`), room list grouped by floor, no JavaScript, access rules, the map view runs one rooms query (fixed count). |

## 2. Out of scope
Zoom, routes, several buildings, occupancy, the pixel-art theme, chat, plans for floors 5–9, clickable shapes.

## 3. Design decisions
**D1. Plan slots are identified by the room number (option a).** The plans have irregular, hand-made geometry; each room slot already carries its number as the label. With an admin-editable slot field, an admin could put room «205» into the slot drawn for «212» (label and data disagree) and we would need a unique-slot constraint and a landmark check again. Linking by number needs no extra field, no admin placement step and no constraint (the number is already unique and validated NNN = floor). Cost: adding a room to the plan is a code change — acceptable for one fixed fictional building. Plan room shapes are drawn always (they are part of the coverage); a missing `Room` row only means that slot cannot be highlighted (the seed creates all of them).

**D2. Geometry as rectangle parts.** Every space is a tuple of disjoint integer rectangles (`parts`); `parts[0]` is the largest part and holds the label. Rectangular spaces have one part and are drawn as `<rect>`; L-shaped spaces have two parts plus explicit `points` and are drawn as `<polygon>`. Coverage is then a pure integer check: each part inside the outline, no part overlaps the corridor, parts pairwise disjoint, Σ areas = outline − corridor ⇒ exact cover with no gaps.

**D3. Portrait sizes.** Outline 392 × 640 units in a 400 × 648 `viewBox`; at 360 px the map is 328 px wide (scale 0.82) and ≈ 531 px tall (vertical scroll only). Side blocks are 160 units wide (131 px), the corridor 72 units. Room numbers stay 20 units (16.4 px); landmark/service labels 15 units (12.3 px), clamped by `textLength` only where the estimate exceeds the label rectangle (computed: «Лестница» 78 > 56 on every floor, «Гардероб» 78 > 64 on floor 1; all others fit).

---

## 4. Architecture

### 4.1 Files
Change:
| File | Change |
|---|---|
| `university/building.py` | rewrite: `Rect`, `Space`, plan constants, `FLOOR_PLANS`, helpers (4.2) |
| `university/models.py` | remove `map_cell`, its two constraints, the `clean()` method (it contains only `super().clean()` and the map-cell check) and the `building` import; remove the `ValidationError` import if it becomes unused |
| `university/migrations/0004_remove_room_map_cell.py` | generated: `makemigrations university --name remove_room_map_cell` |
| `university/admin.py` | `RoomAdmin.list_display = ("number", "floor", "code")` |
| `campusmap/layout.py` | geometry from the plan (4.3); `Rect` re-exported from `university.building` |
| `campusmap/views.py` | `on_map` by number; `floor_plan(floor, current)` (4.4) |
| `campusmap/templates/campusmap/map.html` | polygon shapes, service kind, no plan message, legend (4.5) |
| `static/css/base.css` | polygon and service rules (4.6) |
| `schedule/demo.py` | room seeds from the plan; `RoomSeed` without `map_cell` (4.7) |
| tests | rewrite map/grid tests (6.3); `schedule/tests/test_demo.py` room counts 7 → 39 |
| `README.md` | `## Map` section rewritten; Known limitations bullet updated |

No new app, dependency, setting or env variable.

### 4.2 `university/building.py` (full content)
```python
"""The fictional building: fixed portrait floor plans (one building, floors 1-4).

All geometry is in integer SVG user units. A space is a set of disjoint rectangles;
parts[0] is the largest part and holds the label. Non-rectangular spaces also give
their outline as polygon points.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def cx(self) -> int:
        return self.x + self.width // 2

    @property
    def cy(self) -> int:
        return self.y + self.height // 2

    @property
    def area(self) -> int:
        return self.width * self.height


ROOM = "room"
LANDMARK = "landmark"
SERVICE = "service"


@dataclass(frozen=True)
class Space:
    kind: str                                   # ROOM | LANDMARK | SERVICE
    label: str                                  # room number NNN or a Russian name
    parts: tuple[Rect, ...]                     # disjoint; parts[0] is the label rectangle
    points: tuple[tuple[int, int], ...] = ()    # polygon outline when len(parts) > 1


VIEWBOX_WIDTH = 400
VIEWBOX_HEIGHT = 648
OUTLINE = Rect(4, 4, 392, 640)
CORRIDOR = Rect(164, 84, 72, 488)
STAIRS = Rect(164, 4, 72, 80)
BOTTOM_CENTRE = Rect(164, 572, 72, 72)


def _r(x: int, y: int, w: int, h: int) -> tuple[Rect, ...]:
    return (Rect(x, y, w, h),)


def _room(number: str, x: int, y: int, w: int, h: int) -> Space:
    return Space(ROOM, number, _r(x, y, w, h))


def _landmark(label: str, x: int, y: int, w: int, h: int) -> Space:
    return Space(LANDMARK, label, _r(x, y, w, h))


def _service(label: str, x: int, y: int, w: int, h: int) -> Space:
    return Space(SERVICE, label, _r(x, y, w, h))


_STAIRS = Space(LANDMARK, "Лестница", (STAIRS,))

FLOOR_PLANS: dict[int, tuple[Space, ...]] = {
    1: (
        _STAIRS,
        Space(LANDMARK, "Вход", (BOTTOM_CENTRE,)),
        _room("101", 4, 4, 160, 120),
        _room("102", 4, 124, 160, 80),
        _room("103", 4, 204, 80, 88),
        _room("104", 84, 204, 80, 88),
        _room("105", 4, 292, 160, 96),
        _service("Туалеты", 4, 388, 160, 64),
        Space(
            LANDMARK,
            "Столовая",
            (Rect(4, 452, 160, 104), Rect(84, 556, 80, 88)),
            ((4, 452), (164, 452), (164, 644), (84, 644), (84, 556), (4, 556)),
        ),
        _service("Гардероб", 4, 556, 80, 88),
        _room("106", 236, 4, 160, 104),
        _room("107", 236, 108, 80, 88),
        _room("108", 316, 108, 80, 88),
        _room("114", 236, 196, 160, 120),
        _service("Кафедра", 236, 316, 160, 96),
        _service("Медпункт", 236, 412, 160, 96),
        _service("Склад", 236, 508, 160, 64),
        _service("Охрана", 236, 572, 160, 72),
    ),
    2: (
        _STAIRS,
        Space(SERVICE, "Склад", (BOTTOM_CENTRE,)),
        _landmark("Деканат", 4, 4, 160, 120),
        _room("201", 4, 124, 160, 88),
        _room("202", 4, 212, 160, 88),
        _room("203", 4, 300, 160, 96),
        _room("205", 4, 396, 160, 104),
        _service("Туалеты", 4, 500, 160, 64),
        _room("206", 4, 564, 160, 80),
        _room("207", 236, 4, 160, 96),
        _room("208", 236, 100, 160, 88),
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
        _STAIRS,
        Space(SERVICE, "Склад", (BOTTOM_CENTRE,)),
        _room("301", 4, 4, 160, 104),
        _room("302", 4, 108, 80, 96),
        _room("303", 84, 108, 80, 96),
        _room("304", 4, 204, 160, 112),
        _service("Туалеты", 4, 316, 160, 64),
        _room("305", 4, 380, 160, 88),
        _room("306", 4, 468, 160, 88),
        _room("308", 4, 556, 160, 88),
        _landmark("Библиотека", 236, 4, 160, 200),
        _room("310", 236, 204, 160, 104),
        _room("312", 236, 308, 160, 120),
        _service("Кафедра", 236, 428, 160, 104),
        _room("315", 236, 532, 160, 112),
    ),
    4: (
        _STAIRS,
        Space(SERVICE, "Склад", (BOTTOM_CENTRE,)),
        _room("401", 4, 4, 160, 128),
        _room("402", 4, 132, 160, 96),
        _room("403", 4, 228, 80, 96),
        _room("404", 84, 228, 80, 96),
        _service("Туалеты", 4, 324, 160, 64),
        _room("405", 4, 388, 160, 128),
        _room("406", 4, 516, 160, 128),
        _room("407", 236, 4, 160, 112),
        _room("408", 236, 116, 160, 96),
        _room("409", 236, 212, 160, 144),
        _service("Кафедра", 236, 356, 160, 96),
        _room("410", 236, 452, 160, 96),
        _service("Архив", 236, 548, 160, 96),
    ),
}


def plan_for(floor: int) -> tuple[Space, ...] | None:
    return FLOOR_PLANS.get(floor)


def plan_room_numbers(floor: int) -> frozenset[str]:
    return frozenset(s.label for s in FLOOR_PLANS.get(floor, ()) if s.kind == ROOM)


def all_plan_rooms() -> list[tuple[int, str]]:
    """(floor, number) of every room slot, ordered by floor and number."""
    return sorted((floor, s.label) for floor, spaces in FLOOR_PLANS.items() for s in spaces if s.kind == ROOM)
```
(Keep this exact data: the Planner verified coverage, overlaps, polygon areas and label fit for it, 9.6.)

### 4.3 `campusmap/layout.py`
- Remove `CELL_WIDTH`, `CELL_HEIGHT`, `COLUMN_X`, `ROW_Y`, `cell_rect`, `span_rect`, local `Rect`, `OUTLINE`, `CORRIDOR`, `VIEWBOX_*`; import them from `university.building` (`from university.building import CORRIDOR, LANDMARK, OUTLINE, ROOM, SERVICE, VIEWBOX_HEIGHT, VIEWBOX_WIDTH, Rect, Space, plan_for`). Keep `ROOM_LABEL_SIZE = 20`, `LANDMARK_LABEL_SIZE = 15`, `LABEL_PADDING`, `estimated_label_width`, `label_text_length` unchanged.
- `MapShape`: fields `kind: str`, `label: str`, `rect: Rect` (label rectangle = `parts[0]`; also the drawn rectangle for one-part spaces), `points: str = ""` (SVG `points` attribute for polygons), `is_current: bool = False`, `text_length: int | None = None`.
- `svg_points(points: tuple[tuple[int, int], ...]) -> str` → `" ".join(f"{x},{y}" for x, y in points)` (a Python string, so template localisation never touches the numbers).
- `label_size(kind: str) -> int` → `ROOM_LABEL_SIZE` for rooms, else `LANDMARK_LABEL_SIZE`.
- `floor_plan(floor: int, current: Room | None) -> FloorPlan | None`:
  1. `spaces = plan_for(floor)`; `None` → return `None`.
  2. For each space in order: `rect = space.parts[0]`; `MapShape(kind=space.kind, label=space.label, rect=rect, points=svg_points(space.points), is_current=space.kind == ROOM and current is not None and current.floor == floor and current.number == space.label, text_length=label_text_length(space.label, rect, label_size(space.kind)))`.
  3. Return `FloorPlan(floor, VIEWBOX_WIDTH, VIEWBOX_HEIGHT, OUTLINE, CORRIDOR, shapes)`.
  No queries.

### 4.4 `campusmap/views.py`
- `from university.building import plan_room_numbers` (instead of `blocked_cells`).
- `plan = floor_plan(floor, current) if floor is not None else None`.
- `RoomEntry.on_map = r.number in plan_room_numbers(f)`.
- Everything else unchanged (one rooms query; floors from `Room` rows; 404 rules).
- Context adds `has_plan = plan is not None` (template).

### 4.5 `campusmap/templates/campusmap/map.html`
- Inside the floor branch: `{% if plan %}` … SVG … `{% else %}<p>Схемы {{ current_floor }} этажа нет.</p>{% endif %}` — pass `current_floor` (the selected floor number) in the context.
- Shape element: `{% if s.points %}<polygon points="{{ s.points }}"/>{% else %}<rect x="{{ s.rect.x }}" y="{{ s.rect.y }}" width="{{ s.rect.width }}" height="{{ s.rect.height }}"/>{% endif %}`.
- `<title>`: «Аудитория NNN» for rooms, the label otherwise (unchanged rule).
- Text element unchanged (`class="map-{{ s.kind }}-label"`, `textLength` when set).
- Legend: three items (same swatch markup, classes `map-room`, `map-landmark`, `map-service`): «Аудитория», «Вход, лестница, деканат, библиотека, столовая», «Служебные помещения: гардероб, туалеты, кафедра и другие».

### 4.6 CSS — `static/css/base.css`
Extend the existing selectors so polygons and service spaces are drawn:
- `.map-outline, .map-room rect, .map-room polygon, .map-landmark rect, .map-landmark polygon, .map-service rect, .map-service polygon, .map-corridor { fill: none; stroke: var(--color-text); stroke-width: 2; }` (replace the current group).
- `.map-landmark rect, .map-landmark polygon { stroke: var(--color-muted); stroke-dasharray: 6 4; }`
- New: `.map-service rect, .map-service polygon { stroke: var(--color-muted); stroke-dasharray: 2 3; }` and `.map-service-label { font-size: 15px; fill: var(--color-muted); }`.
- Keep `.map-current .map-room-label` and `a.map-current` unchanged.

### 4.7 Seed — `schedule/demo.py`
- `RoomSeed` loses `map_cell`. Replace `ROOM_SEEDS` with
  `ROOM_SEEDS = [RoomSeed(code=f"room-{number}", floor=floor, number=number) for floor, number in all_plan_rooms()]` (`from university.building import all_plan_rooms`).
- Room loop: `room = Room.objects.filter(code=seed.code).first() or Room(code=seed.code)`; `room.floor, room.number = seed.floor, seed.number`; `full_clean()`; `save()` (the existing conflict handling stays).
- `ScheduleSeedSummary.rooms = len(ROOM_SEEDS)` → 39. `LESSON_SEEDS` / `CHANGE_SEEDS` keep using `room-101` … `room-402`.

### 4.8 README
`## Map`: portrait plans for floors 1–4 in `university/building.py`; a room appears when its number is a slot on its floor's plan (no admin placement; to add a room to the plan, change the code); rooms elsewhere show «нет на схеме»; L-shaped spaces; legend; highlight unchanged. Known limitations: replace the 9-cell grid bullet with «Plans exist for floors 1–4 only; a room is drawn only if its number is a slot in `university/building.py`.»

---

## 5. Functions and tests (summary)
| Function | Tests |
|---|---|
| `building.FLOOR_PLANS`, `plan_for`, `plan_room_numbers`, `all_plan_rooms` | `university/tests/test_building.py::FloorPlanTests` |
| `layout.svg_points`, `label_size`, `floor_plan` | `campusmap/tests/test_layout.py::LayoutTests` |
| `MapView` (on_map, no plan) | `campusmap/tests/test_views.py` |
| `Room` without `map_cell` | `university/tests/test_models.py`, `test_admin.py` |
| seed | `schedule/tests/test_demo.py` |

---

## 6. Test plan

### 6.0 Rules
Pure geometry tests use `SimpleTestCase`. View tests create `Room` rows directly (no `map_cell`). Page assertions follow the TASK-008-FIX rule (exact markup). Save every test log; report any failed or stalled run by test name and Moscow time.

### 6.1 Traceability
| AC | Tests |
|---|---|
| AC1 | `FloorPlanTests::test_fixed_elements_same_on_every_floor`, `test_plans_for_floors_1_to_4_only` |
| AC2 | `FloorPlanTests::test_full_coverage_no_overlap` (per floor, subTest) |
| AC3 | `FloorPlanTests::test_room_numbers`, `test_demo_rooms_on_plan`, `test_l_shapes_are_polygons_with_matching_area`, `test_polygon_vertices_are_part_corners` |
| AC4 | `FloorPlanTests::test_landmarks_and_services_per_floor`; `campusmap/tests/test_views.py::MapViewTests::test_legend_has_three_kinds` |
| AC5 | `LayoutTests::test_viewbox_portrait`, `test_labels_fit_with_padding`, `test_clamped_labels_exactly`, `test_room_label_size_unchanged`; `MapViewTests::test_svg_scales` (existing, viewBox `0 0 400 648`) |
| AC6 | `MapViewTests::test_room_on_plan_by_number`, `test_room_not_on_plan_listed`, `test_floor_without_plan`, `test_highlight_polygon_room`; `university/tests/test_models.py::RoomModelTests::test_no_map_cell_field`; migration check (section 8) |
| AC7 | `schedule/tests/test_demo.py::ScheduleDemoTests::test_seed_creates_all_plan_rooms`, `test_seed_twice_same_rooms`, `test_demo_room_codes_kept` |
| AC8 | existing `MapAccessTests`, `MapViewTests` (switcher, highlight, 404s, list), `MapQueryTests`, `MapNavTests`, `schedule` `RoomLinkTests` — kept, adapted only where they used `map_cell` |

### 6.2 Access matrix
Unchanged from TASK-008 6.2 (`MapAccessTests`): anonymous 302; student, student without profile, staff, superuser 200 on `/map/`, `/map/floor/2/`, `/map/room/room-205/`; POST 405. Keep all cells.

### 6.3 Test details
`university/tests/test_building.py` — replace `BuildingTests` with `FloorPlanTests(SimpleTestCase)`:
- `test_plans_for_floors_1_to_4_only` (`sorted(FLOOR_PLANS) == [1, 2, 3, 4]`; `plan_for(5) is None`)
- `test_fixed_elements_same_on_every_floor` (each plan has exactly one space whose `parts == (STAIRS,)` labelled «Лестница», and exactly one space whose `parts == (BOTTOM_CENTRE,)`; `CORRIDOR` is not a part of any space)
- `test_full_coverage_no_overlap` (for each floor, `subTest(floor=…)`: all parts inside `OUTLINE`; no part has a positive-area intersection with `CORRIDOR`; parts pairwise without positive-area intersection; `sum(part.area) == OUTLINE.area - CORRIDOR.area`). Helper `_intersection_area(a, b)` with integer arithmetic in the test module.
- `test_room_numbers` (per floor: every room label is 3 digits, first digit = floor; all 39 numbers unique; counts 9, 10, 10, 10)
- `test_demo_rooms_on_plan` ({101, 114, 205, 212, 308, 315, 402} ⊆ numbers on their floors)
- `test_l_shapes_are_polygons_with_matching_area` (exactly the spaces «Столовая» (1) and «210» (2) have 2 parts; shoelace area of `points` == sum of part areas; `parts[0].area > parts[1].area`)
- `test_polygon_vertices_are_part_corners` (each polygon vertex is a corner of one of the space's parts)
- `test_landmarks_and_services_per_floor` (landmark labels: 1 → {Лестница, Вход, Столовая}, 2 → {Лестница, Деканат}, 3 → {Лестница, Библиотека}, 4 → {Лестница}; «Туалеты» on every floor; «Гардероб» on floor 1)
- `test_all_plan_rooms_sorted` (39 tuples; first `(1, "101")`, last `(4, "410")`)

`campusmap/tests/test_layout.py` — rewrite `LayoutTests(SimpleTestCase)`:
- `test_viewbox_portrait` (`VIEWBOX_WIDTH == 400`, `VIEWBOX_HEIGHT == 648`, height > width)
- `test_room_label_size_unchanged` (`ROOM_LABEL_SIZE == 20`, `LANDMARK_LABEL_SIZE == 15`; `ROOM_LABEL_SIZE * 328 / VIEWBOX_WIDTH >= 16`, `LANDMARK_LABEL_SIZE * 328 / VIEWBOX_WIDTH >= 12`)
- `test_labels_fit_with_padding` (every shape of `floor_plan(f, None)` for f in 1–4: `min(estimated_label_width(label, label_size(kind)), text_length or 10**6) <= rect.width - 2 * LABEL_PADDING`; `rect.height >= 48`)
- `test_clamped_labels_exactly` (the set of `(floor, label)` with `text_length` is `{(1, "Лестница"), (2, "Лестница"), (3, "Лестница"), (4, "Лестница"), (1, "Гардероб")}`; room shapes never clamped)
- `test_polygon_points_string` (`svg_points(((4, 452), (164, 452)))` == `"4,452 164,452"`; «Столовая» shape `points` starts with `"4,452 "`)
- `test_coordinates_are_integers` (all `Rect` fields, `cx`, `cy` are `int`)
- `test_floor_plan_marks_current` (`Room(floor=4, number="402", code="room-402")` unsaved → exactly one shape `is_current`, label «402»)
- `test_current_on_other_floor_not_marked` (current room 101 → no shape current on floor 2)
- `test_no_plan_for_floor_5` (`floor_plan(5, None) is None`)

`campusmap/tests/test_views.py` — adapt `setUpTestData` (remove `map_cell=`; for the "not on plan" case use a room NOT in the plan, e.g. `Room(code="room-199", floor=1, number="199")` instead of 114 without a cell). Add/adapt in `MapViewTests`:
- `test_room_on_plan_by_number` (room 114 exists → list item has no «нет на схеме»; the SVG contains `<title>Аудитория 114</title>`)
- `test_room_not_on_plan_listed` (`199</a> — нет на схеме`; `/map/room/room-199/` → 200, floor 1, no `map-current` inside the SVG, list link marked)
- `test_floor_without_plan` (create `Room(code="room-501", floor=5, number="501")` → `/map/floor/5/` → 200, «Схемы 5 этажа нет.», no `<svg class="map-svg"`, «501</a> — нет на схеме»)
- `test_highlight_polygon_room` (create room 210 → `/map/room/room-210/` → inside the SVG one `class="map-room map-current"` group containing `<polygon points="236,188 396,188 396,316 316,316 316,412 236,412"/>`)
- `test_legend_has_three_kinds` (three swatches: `class="map-room"`, `class="map-landmark"`, `class="map-service"`; text «Служебные помещения»)
- Adapt `test_landmarks_per_floor` (floor 4 now also has service labels; assert landmark labels via `class="map-landmark-label"` elements only) and `test_svg_scales` (`viewBox="0 0 400 648"`).
- `MapQueryTests`: keep `test_queries_constant` (4 vs 20 rooms; use plan numbers or off-plan numbers, both fine) and `test_highlight_view_same_queries`.

`university/tests/test_models.py` — delete `RoomMapCellTests`; add `RoomModelTests::test_no_map_cell_field` (`"map_cell" not in [f.name for f in Room._meta.get_fields()]`). Keep `RoomNumberTests` unchanged.
`university/tests/test_admin.py` — remove `map_cell` from all POST data; delete `test_landmark_cell_shows_error` and `test_duplicate_cell_shows_error`; keep `test_valid_room_saved`, `test_bad_number_shows_field_error`, `test_mismatch_shows_error`.
`schedule/tests/test_demo.py` — counts 7 → 39 (`summary.rooms`, `Room.objects.count()`); replace the `map_cell` assertions with `test_seed_creates_all_plan_rooms` (every `(floor, number)` of `all_plan_rooms()` has a `Room` with code `room-<number>` and that floor; every row passes `full_clean()`), `test_seed_twice_same_rooms` (39 after two runs, same pks), `test_demo_room_codes_kept` (the 7 demo codes exist and the seeded weekly lessons still reference them).

### 6.4 Settings branches / query count
No settings change. Map view query count unchanged (one rooms query; plan data is code).

---

## 7. Implementation order
1. `university/building.py` rewrite + `test_building.py` (coverage tests must pass on the given data).
2. Remove `map_cell` (model, admin), generate migration 0004; adapt `university` tests.
3. `campusmap/layout.py`, views, template, CSS; adapt/add campusmap tests.
4. Seed + `schedule/tests/test_demo.py`; README.
5. `ruff format` on changed Python files only (not migrations); section 8; `REPORT` to the Reviewer. Do not commit.

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
node --check static/js/chat.js && echo "js syntax ok"
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"
export DATABASE_URL="sqlite:///$TMPDIR/task010.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task010-private" DEMO_PASSWORD='Local-Demo-Pass-2026!'
rm -f "$TMPDIR/task010.sqlite3"
python manage.py migrate && python manage.py seed_demo && python manage.py seed_demo
# Migration on data seeded BEFORE the change (old code from git, temporary copy only)
rm -rf "$TMPDIR/task010-old" "$TMPDIR/task010-old.sqlite3" && mkdir "$TMPDIR/task010-old" && git archive 08671f6 | tar -x -C "$TMPDIR/task010-old"
(cd "$TMPDIR/task010-old" && DATABASE_URL="sqlite:///$TMPDIR/task010-old.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task010-old-private" python manage.py migrate -v0 && DATABASE_URL="sqlite:///$TMPDIR/task010-old.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task010-old-private" python manage.py seed_demo)
DATABASE_URL="sqlite:///$TMPDIR/task010-old.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task010-old-private" python manage.py migrate
DATABASE_URL="sqlite:///$TMPDIR/task010-old.sqlite3" PRIVATE_MEDIA_ROOT="$TMPDIR/task010-old-private" python manage.py seed_demo
git status --short
```
`REPORT`: output tails, test count (was 963), log file names, any failed or stalled run by test name and Moscow time, the old-DB migration output (7 rooms before, 39 after the second seed), `git status`.

## 9. Feasibility check (2026-11-16 14:23 MSK on `08671f6`)
1. Clean start — `git status --short` → only ` M plan.md`. OK.
2. Referenced objects — `university/building.py` (grid: `MapCell`, `STAIRS_CELL`, `Landmark`, `LANDMARKS`, `landmarks_on`, `blocked_cells`); `Room.map_cell` + constraints `university_room_map_cell_value`, `university_room_unique_map_cell` + `clean()` (only the landmark-cell check) (`university/models.py:6, 102-108, 133-139, 149-153`); migration `0003_room_number_format_and_map_cell`; `RoomAdmin.list_display` with `map_cell` (`university/admin.py:28`); `campusmap/layout.py` (`Rect`, `OUTLINE`, `CORRIDOR`, `cell_rect`, `span_rect`, `floor_plan(floor, rooms, current)`, label helpers); `campusmap/views.py:59` (`on_map` via `blocked_cells`); `map.html` (rect-only shapes, legend 2 items); `schedule/demo.py:32, 75-81, 255` (`RoomSeed.map_cell`, loop); tests using the grid or `map_cell`: `campusmap/tests/test_views.py`, `test_layout.py`, `schedule/tests/test_demo.py` (counts 7, cell checks), `university/tests/test_admin.py`, `test_models.py` (`RoomMapCellTests`), `test_building.py`; README `## Map` (line ~154). No other code uses `map_cell` or the grid. OK.
3. No collisions — no `FLOOR_PLANS`, `Space`, `plan_for`, `plan_room_numbers`, `all_plan_rooms`, `svg_points`, `label_size`, CSS `map-service`; latest university migration is `0003`. OK.
4. Migrations — on a temporary copy of `HEAD` with `map_cell` removed (model, constraints, `clean()`, admin column): `makemigrations university --name remove_room_map_cell` → `0004_remove_room_map_cell.py` (RemoveConstraint × 2, RemoveField); applied on a DB seeded with the CURRENT code → OK, 7 rooms kept (`101/1 … 402/4`). OK.
5. Tools — unchanged. OK.
6. Framework / geometry — the plan data in 4.2 was checked with a script (`$TMPDIR/t010/plan_check.py`): every floor: all parts inside the outline, none overlaps the corridor, no pairwise overlaps, Σ areas = 250 880 − 35 136 = 215 744 = outline − corridor; polygon (shoelace) areas equal the part sums for «Столовая» and «210»; 39 rooms (9/10/10/10), all NNN with first digit = floor, unique; label fit: only «Лестница» (78 > 56, floors 1–4) and «Гардероб» (78 > 64, floor 1) need `textLength`; every label rectangle ≥ 64 units high. SVG `<polygon points>` is standard. OK.
7. Environment — nothing new. OK.
8. Verification runnable — 9a.
9. Conflicts — none.
10. Assumptions / blockers — none.

### 9a. Verification results on the current tree
Logs `$TMPDIR/test-20261116-142330-t010-feas*.log`.
- `check` → no issues; `makemigrations --check --dry-run` → «No changes detected».
- `test` → `Ran 963 tests … OK`; `run_tests_at.py 2026-11-17T23:59:59` → 963 OK; `run_tests_at.py 2026-11-18T00:00:00` → 963 OK. No failed or stalled runs.
- `check --deploy --fail-level WARNING` → no issues (1 silenced); `ruff check .` → all passed; `ruff format --check .` → 183 files already formatted; `node --check static/js/chat.js` → ok; CI YAML ok.
- `seed_demo` twice on a temporary DB and PRIVATE_MEDIA_ROOT → OK (second run «Chat ready: 0 dialogs, 0 messages.»).

## 10. Risks
- **Plan data typos** break coverage — the coverage test fails immediately; copy the data from 4.2 verbatim.
- **Room rows vs plan**: plan rooms without a `Room` row are drawn but cannot be highlighted; the seed creates all 39.
- **Migration**: removes a column with data (cell positions) — no longer needed by design; the demo positions are now in code. Local and server DBs keep all rooms.
- **Taller page**: the map is ≈ 531 px high at 360 px; the room list follows below (unchanged, UI stage).
