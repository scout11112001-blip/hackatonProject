from django.test import SimpleTestCase

from campusmap.layout import (
    LABEL_PADDING,
    LANDMARK_LABEL_SIZE,
    ROOM_LABEL_SIZE,
    VIEWBOX_HEIGHT,
    VIEWBOX_WIDTH,
    estimated_label_width,
    floor_plan,
    label_size,
    svg_points,
)
from university.building import CORRIDOR, FLOOR_PLANS, OUTLINE
from university.models import Room


class LayoutTests(SimpleTestCase):
    def test_viewbox_portrait(self):
        self.assertEqual(VIEWBOX_WIDTH, 400)
        self.assertEqual(VIEWBOX_HEIGHT, 648)
        self.assertGreater(VIEWBOX_HEIGHT, VIEWBOX_WIDTH)

    def test_room_label_size_unchanged(self):
        self.assertEqual(ROOM_LABEL_SIZE, 20)
        self.assertEqual(LANDMARK_LABEL_SIZE, 15)
        self.assertGreaterEqual(ROOM_LABEL_SIZE * 328 / VIEWBOX_WIDTH, 16)
        self.assertGreaterEqual(LANDMARK_LABEL_SIZE * 328 / VIEWBOX_WIDTH, 12)

    def test_labels_fit_with_padding(self):
        for floor in range(1, 5):
            plan = floor_plan(floor, None)
            self.assertIsNotNone(plan)
            for shape in plan.shapes:
                size = label_size(shape.kind)
                estimated = estimated_label_width(shape.label, size)
                used = min(estimated, shape.text_length or 10**6)
                self.assertLessEqual(
                    used,
                    shape.rect.width - 2 * LABEL_PADDING,
                    f"{shape.label} on floor {floor}",
                )
                self.assertGreaterEqual(shape.rect.height, 48, shape.label)

    def test_clamped_labels_exactly(self):
        clamped = set()
        lengths = []
        for floor in range(1, 5):
            plan = floor_plan(floor, None)
            for shape in plan.shapes:
                if shape.text_length is not None:
                    clamped.add((floor, shape.label))
                    lengths.append((floor, shape.label, shape.text_length))
        # TASK-013: two staircases per floor; Охрана and Гардероб are small rooms by the entrance.
        self.assertEqual(
            clamped,
            {(f, "Лестница") for f in range(1, 5)} | {(1, "Охрана"), (1, "Гардероб")},
        )
        for floor in range(1, 5):
            stairs = [n for f, label, n in lengths if f == floor and label == "Лестница"]
            self.assertEqual(stairs, [56, 56], f"floor {floor}")
        self.assertIn((1, "Охрана", 56), lengths)
        self.assertIn((1, "Гардероб", 72), lengths)
        for floor in range(1, 5):
            plan = floor_plan(floor, None)
            for shape in plan.shapes:
                if shape.kind == "room":
                    self.assertIsNone(shape.text_length, shape.label)

    def test_polygon_points_string(self):
        self.assertEqual(svg_points(((4, 452), (164, 452))), "4,452 164,452")
        # TASK-013: the canteen is a rectangle now; room 210 is the only polygon.
        plan = floor_plan(2, None)
        room = next(s for s in plan.shapes if s.label == "210")
        self.assertEqual(room.points, "236,188 396,188 396,316 316,316 316,412 236,412")

    def test_coordinates_are_integers(self):
        rects = [OUTLINE, CORRIDOR]
        for spaces in FLOOR_PLANS.values():
            for space in spaces:
                rects.extend(space.parts)
        for rect in rects:
            for value in (rect.x, rect.y, rect.width, rect.height, rect.cx, rect.cy):
                self.assertIsInstance(value, int)

    def test_floor_plan_marks_current(self):
        room = Room(floor=4, number="402", code="room-402")
        plan = floor_plan(4, room)
        current = [s for s in plan.shapes if s.is_current]
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0].label, "402")

    def test_current_on_other_floor_not_marked(self):
        room = Room(floor=1, number="101", code="room-101")
        plan = floor_plan(2, room)
        self.assertFalse([s for s in plan.shapes if s.is_current])

    def test_no_plan_for_floor_5(self):
        self.assertIsNone(floor_plan(5, None))
