from django.test import SimpleTestCase

from campusmap.layout import (
    CELL_WIDTH,
    CORRIDOR,
    LABEL_PADDING,
    LANDMARK_LABEL_SIZE,
    OUTLINE,
    ROOM_LABEL_SIZE,
    VIEWBOX_WIDTH,
    cell_rect,
    estimated_label_width,
    floor_plan,
    span_rect,
)
from university.building import LANDMARKS, STAIRS_CELL, MapCell
from university.models import Room


def _inside(rect, box):
    return (
        rect.x >= box.x
        and rect.y >= box.y
        and rect.x + rect.width <= box.x + box.width
        and rect.y + rect.height <= box.y + box.height
    )


def _overlaps(a, b):
    return not (
        a.x + a.width <= b.x
        or b.x + b.width <= a.x
        or a.y + a.height <= b.y
        or b.y + b.height <= a.y
    )


def _room(floor, number, cell, pk=None):
    room = Room(code=f"room-{number}", floor=floor, number=number, map_cell=cell)
    if pk is not None:
        room.pk = pk
    return room


class LayoutTests(SimpleTestCase):
    def test_cells_inside_viewbox_and_disjoint(self):
        cells = [*MapCell.values, STAIRS_CELL]
        room_rects = [cell_rect(c) for c in MapCell.values]
        for c in cells:
            self.assertTrue(_inside(cell_rect(c), OUTLINE), f"cell {c} outside outline")
            self.assertFalse(_overlaps(cell_rect(c), CORRIDOR), f"cell {c} overlaps corridor")
        for i, a in enumerate(room_rects):
            for b in room_rects[i + 1 :]:
                self.assertFalse(_overlaps(a, b))
        for lm in LANDMARKS:
            self.assertTrue(_inside(span_rect(lm.cells), OUTLINE), f"{lm.key} outside outline")
            self.assertFalse(
                _overlaps(span_rect(lm.cells), CORRIDOR), f"{lm.key} overlaps corridor"
            )

    def test_coordinates_are_integers(self):
        rects = [OUTLINE, CORRIDOR]
        rects += [cell_rect(c) for c in [*MapCell.values, STAIRS_CELL]]
        rects += [span_rect(lm.cells) for lm in LANDMARKS]
        for rect in rects:
            for value in (rect.x, rect.y, rect.width, rect.height, rect.cx, rect.cy):
                self.assertIsInstance(value, int)

    def test_label_sizes(self):
        self.assertGreaterEqual(ROOM_LABEL_SIZE * 328 / VIEWBOX_WIDTH, 16)
        self.assertGreaterEqual(LANDMARK_LABEL_SIZE * 328 / VIEWBOX_WIDTH, 12)

    def test_landmark_labels_fit_with_padding(self):
        for floor in range(1, 10):
            plan = floor_plan(floor, [], None)
            for shape in plan.shapes:
                if shape.kind != "landmark":
                    continue
                estimated = estimated_label_width(shape.label, LANDMARK_LABEL_SIZE)
                used = min(estimated, shape.text_length or 10**6)
                self.assertLessEqual(
                    used,
                    shape.rect.width - 2 * LABEL_PADDING,
                    f"{shape.label} on floor {floor}",
                )

    def test_stairs_label_clamped(self):
        plan = floor_plan(1, [], None)
        stairs = next(s for s in plan.shapes if s.label == "Лестница")
        self.assertEqual(stairs.text_length, CELL_WIDTH - 2 * LABEL_PADDING)

    def test_rooms_never_clamped(self):
        rooms = [_room(1, "101", "N2"), _room(1, "102", "N3")]
        plan = floor_plan(1, rooms, None)
        for shape in plan.shapes:
            if shape.kind == "room":
                self.assertIsNone(shape.text_length)
        self.assertLessEqual(
            estimated_label_width("888", ROOM_LABEL_SIZE), CELL_WIDTH - 2 * LABEL_PADDING
        )

    def test_floor_plan_marks_current(self):
        r1 = _room(1, "101", "N2", pk=1)
        r2 = _room(1, "102", "N3", pk=2)
        plan = floor_plan(1, [r1, r2], r2)
        current = [s for s in plan.shapes if s.is_current]
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0].label, "102")

    def test_room_without_cell_not_drawn(self):
        r = _room(1, "101", "")
        plan = floor_plan(1, [r], None)
        self.assertNotIn("101", [s.label for s in plan.shapes if s.kind == "room"])

    def test_room_on_blocked_cell_not_drawn(self):
        r = _room(1, "101", STAIRS_CELL)
        plan = floor_plan(1, [r], None)
        self.assertNotIn("101", [s.label for s in plan.shapes if s.kind == "room"])

    def test_other_floor_rooms_not_drawn(self):
        r = _room(2, "201", "N2", pk=1)
        plan = floor_plan(1, [r], None)
        self.assertNotIn("201", [s.label for s in plan.shapes if s.kind == "room"])
