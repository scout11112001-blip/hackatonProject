from django.test import SimpleTestCase

from university.building import (
    CORRIDOR,
    DOOR_MIN,
    FLOOR_PLANS,
    INNER_ROOMS,
    LANDMARK,
    OUTLINE,
    ROOM,
    SERVICE,
    STAIRS,
    STAIRS_BOTTOM,
    TOILET,
    Rect,
    Space,
    all_plan_rooms,
    plan_for,
    plan_room_numbers,
)


def _intersection_area(a, b):
    w = min(a.x + a.width, b.x + b.width) - max(a.x, b.x)
    h = min(a.y + a.height, b.y + b.height) - max(a.y, b.y)
    return w * h if w > 0 and h > 0 else 0


def _inside(rect, box):
    return (
        rect.x >= box.x
        and rect.y >= box.y
        and rect.x + rect.width <= box.x + box.width
        and rect.y + rect.height <= box.y + box.height
    )


def _polygon_area(points):
    total = 0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return abs(total) // 2


def _shared_wall(a: Rect, b: Rect) -> int:
    """Length of the common boundary of two non-overlapping rectangles."""
    if a.x + a.width == b.x or b.x + b.width == a.x:
        return max(0, min(a.y + a.height, b.y + b.height) - max(a.y, b.y))
    if a.y + a.height == b.y or b.y + b.height == a.y:
        return max(0, min(a.x + a.width, b.x + b.width) - max(a.x, b.x))
    return 0


def _space_wall(space: Space, rects: list[Rect]) -> int:
    return max((_shared_wall(p, r) for p in space.parts for r in rects), default=0)


def _find(floor: int, label: str) -> list[Space]:
    return [s for s in FLOOR_PLANS[floor] if s.label == label]


def _part_corners(rect):
    return {
        (rect.x, rect.y),
        (rect.x + rect.width, rect.y),
        (rect.x + rect.width, rect.y + rect.height),
        (rect.x, rect.y + rect.height),
    }


class FloorPlanTests(SimpleTestCase):
    def test_plans_for_floors_1_to_4_only(self):
        self.assertEqual(sorted(FLOOR_PLANS), [1, 2, 3, 4])
        self.assertIsNone(plan_for(5))

    # TASK-013: two staircases (top and bottom of the corridor) replace STAIRS + BOTTOM_CENTRE.
    def test_two_staircases_same_place(self):
        for floor, spaces in FLOOR_PLANS.items():
            with self.subTest(floor=floor):
                for rect in (STAIRS, STAIRS_BOTTOM):
                    stairs = [s for s in spaces if s.parts == (rect,)]
                    self.assertEqual(len(stairs), 1, f"no single space at {rect}")
                    self.assertEqual(stairs[0].label, "Лестница")
                    self.assertEqual(stairs[0].kind, LANDMARK)
                self.assertEqual(len([s for s in spaces if s.label == "Лестница"]), 2)
                for s in spaces:
                    for part in s.parts:
                        self.assertNotEqual(part, CORRIDOR)

    def test_no_storage(self):
        for floor, spaces in FLOOR_PLANS.items():
            with self.subTest(floor=floor):
                self.assertNotIn("Склад", {s.label for s in spaces})

    def test_entrance_only_on_floor_1(self):
        for floor in (2, 3, 4):
            self.assertEqual(_find(floor, "Вход"), [], f"Вход on floor {floor}")
        entrances = _find(1, "Вход")
        self.assertEqual(len(entrances), 1)
        entrance = entrances[0]
        self.assertEqual(entrance.kind, LANDMARK)
        self.assertEqual(entrance.parts, (Rect(236, 500, 160, 72),))
        self.assertGreaterEqual(_space_wall(entrance, [CORRIDOR]), DOOR_MIN)

    def test_wardrobe_and_security_next_to_entrance(self):
        entrance = _find(1, "Вход")[0]
        (wardrobe,) = _find(1, "Гардероб")
        (security,) = _find(1, "Охрана")
        for space in (wardrobe, security):
            with self.subTest(label=space.label):
                self.assertEqual(space.kind, SERVICE)
                self.assertEqual(len(space.parts), 1)
                self.assertGreaterEqual(_space_wall(space, list(entrance.parts)), DOOR_MIN)
        self.assertLessEqual(security.parts[0].area, 72 * 72)
        (canteen,) = _find(1, "Столовая")
        self.assertEqual(_space_wall(wardrobe, list(canteen.parts)), 0)
        self.assertEqual(len(canteen.parts), 1)
        self.assertEqual(canteen.points, ())

    def test_rooms_open_to_corridor(self):
        self.assertEqual(INNER_ROOMS, {"211"})
        for floor, spaces in FLOOR_PLANS.items():
            for s in spaces:
                if s.kind != ROOM or s.label in INNER_ROOMS:
                    continue
                with self.subTest(floor=floor, label=s.label):
                    self.assertGreaterEqual(_space_wall(s, [CORRIDOR]), DOOR_MIN)
        (inner,) = _find(2, "211")
        (outer,) = _find(2, "210")
        self.assertGreaterEqual(_space_wall(inner, list(outer.parts)), DOOR_MIN)

    def test_other_spaces_open_to_corridor_or_entrance(self):
        for floor, spaces in FLOOR_PLANS.items():
            entrance_parts = [p for s in spaces if s.label == "Вход" for p in s.parts]
            for s in spaces:
                if s.kind == ROOM:
                    continue
                with self.subTest(floor=floor, label=s.label, parts=s.parts):
                    if s.label == "Лестница":
                        self.assertEqual(_space_wall(s, [CORRIDOR]), 72)
                        continue
                    access = max(_space_wall(s, [CORRIDOR]), _space_wall(s, entrance_parts))
                    self.assertGreaterEqual(access, DOOR_MIN)

    def test_one_toilet_per_floor_in_one_riser(self):
        expected = {1: "Туалет М", 2: "Туалет Ж", 3: "Туалет М", 4: "Туалет Ж"}
        for floor, spaces in FLOOR_PLANS.items():
            with self.subTest(floor=floor):
                toilets = [s for s in spaces if s.label.startswith("Туалет")]
                self.assertEqual(len(toilets), 1)
                self.assertEqual(toilets[0].label, expected[floor])
                self.assertEqual(toilets[0].kind, SERVICE)
                self.assertEqual(toilets[0].parts, (TOILET,))

    def test_shared_wall_helper(self):
        self.assertEqual(_shared_wall(Rect(0, 0, 10, 40), Rect(10, 0, 10, 40)), 40)
        self.assertEqual(_shared_wall(Rect(0, 0, 10, 10), Rect(10, 10, 10, 10)), 0)
        self.assertEqual(_shared_wall(Rect(0, 0, 10, 10), Rect(30, 30, 10, 10)), 0)
        self.assertEqual(_shared_wall(Rect(0, 0, 40, 10), Rect(16, 10, 40, 10)), 24)

    def test_full_coverage_no_overlap(self):
        for floor, spaces in FLOOR_PLANS.items():
            with self.subTest(floor=floor):
                parts = [part for s in spaces for part in s.parts]
                for part in parts:
                    self.assertTrue(_inside(part, OUTLINE), f"part {part} outside outline")
                    self.assertEqual(
                        _intersection_area(part, CORRIDOR),
                        0,
                        f"part {part} overlaps corridor",
                    )
                for i, a in enumerate(parts):
                    for b in parts[i + 1 :]:
                        self.assertEqual(_intersection_area(a, b), 0, f"parts {a} and {b} overlap")
                self.assertEqual(
                    sum(p.area for p in parts),
                    OUTLINE.area - CORRIDOR.area,
                    f"floor {floor} does not exactly cover outline minus corridor",
                )

    def test_room_numbers(self):
        counts = {}
        all_numbers = []
        for floor, spaces in FLOOR_PLANS.items():
            numbers = [s.label for s in spaces if s.kind == ROOM]
            counts[floor] = len(numbers)
            for number in numbers:
                self.assertEqual(len(number), 3, f"{number} not 3 digits")
                self.assertEqual(int(number[0]), floor, f"{number} first digit != floor")
                all_numbers.append(number)
        self.assertEqual(counts, {1: 9, 2: 10, 3: 10, 4: 10})
        self.assertEqual(len(all_numbers), 39)
        self.assertEqual(len(set(all_numbers)), 39, "duplicate room numbers")

    def test_demo_rooms_on_plan(self):
        demo = {"101": 1, "114": 1, "205": 2, "212": 2, "308": 3, "315": 3, "402": 4}
        for number, floor in demo.items():
            with self.subTest(number=number):
                self.assertIn(number, plan_room_numbers(floor))

    def test_l_shapes_are_polygons_with_matching_area(self):
        multi = [s for spaces in FLOOR_PLANS.values() for s in spaces if len(s.parts) > 1]
        # TASK-013: the canteen is one rectangle now; 210 is the only multi-part space.
        self.assertEqual({(s.kind, s.label) for s in multi}, {(ROOM, "210")})
        for s in multi:
            self.assertEqual(len(s.parts), 2, s.label)
            self.assertEqual(_polygon_area(s.points), sum(p.area for p in s.parts), s.label)
            self.assertGreater(s.parts[0].area, s.parts[1].area, s.label)

    def test_polygon_vertices_are_part_corners(self):
        for spaces in FLOOR_PLANS.values():
            for s in spaces:
                if not s.points:
                    continue
                corners = set().union(*(_part_corners(p) for p in s.parts))
                for vertex in s.points:
                    self.assertIn(vertex, corners, f"{s.label} vertex {vertex} not a part corner")

    def test_landmarks_and_services_per_floor(self):
        def labels(floor, kind):
            return {s.label for s in FLOOR_PLANS[floor] if s.kind == kind}

        self.assertEqual(labels(1, LANDMARK), {"Лестница", "Вход", "Столовая"})
        self.assertEqual(labels(2, LANDMARK), {"Лестница", "Деканат"})
        self.assertEqual(labels(3, LANDMARK), {"Лестница", "Библиотека"})
        self.assertEqual(labels(4, LANDMARK), {"Лестница"})
        # TASK-013: one toilet per floor, no "Склад", Охрана + Гардероб at the entrance.
        self.assertEqual(
            {f: labels(f, SERVICE) for f in (1, 2, 3, 4)},
            {
                1: {"Туалет М", "Кафедра", "Медпункт", "Охрана", "Гардероб"},
                2: {"Туалет Ж", "Кафедра"},
                3: {"Туалет М", "Кафедра"},
                4: {"Туалет Ж", "Кафедра", "Архив"},
            },
        )

    def test_all_plan_rooms_sorted(self):
        rooms = all_plan_rooms()
        self.assertEqual(len(rooms), 39)
        self.assertEqual(rooms[0], (1, "101"))
        self.assertEqual(rooms[-1], (4, "410"))
