from django.test import SimpleTestCase

from university.building import (
    BOTTOM_CENTRE,
    CORRIDOR,
    FLOOR_PLANS,
    LANDMARK,
    OUTLINE,
    ROOM,
    SERVICE,
    STAIRS,
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

    def test_fixed_elements_same_on_every_floor(self):
        for floor, spaces in FLOOR_PLANS.items():
            with self.subTest(floor=floor):
                stairs = [s for s in spaces if s.parts == (STAIRS,)]
                self.assertEqual(len(stairs), 1, "no single STAIRS space")
                self.assertEqual(stairs[0].label, "Лестница")
                self.assertEqual(stairs[0].kind, LANDMARK)
                bottom = [s for s in spaces if s.parts == (BOTTOM_CENTRE,)]
                self.assertEqual(len(bottom), 1, "no single BOTTOM_CENTRE space")
                for s in spaces:
                    for part in s.parts:
                        self.assertNotEqual(part, CORRIDOR)

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
        self.assertEqual(
            {(s.kind, s.label) for s in multi}, {(LANDMARK, "Столовая"), (ROOM, "210")}
        )
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
        for floor in (1, 2, 3, 4):
            self.assertIn("Туалеты", labels(floor, SERVICE), f"no Туалеты on {floor}")
        self.assertIn("Гардероб", labels(1, SERVICE))
        self.assertNotIn("Гардероб", labels(2, SERVICE))

    def test_all_plan_rooms_sorted(self):
        rooms = all_plan_rooms()
        self.assertEqual(len(rooms), 39)
        self.assertEqual(rooms[0], (1, "101"))
        self.assertEqual(rooms[-1], (4, "410"))
