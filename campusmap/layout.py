"""Geometry for the schematic building plan. All values are integers."""

from collections.abc import Sequence
from dataclasses import dataclass

from university.building import blocked_cells, landmarks_on
from university.models import Room

VIEWBOX_WIDTH = 400
VIEWBOX_HEIGHT = 240
ROOM_LABEL_SIZE = 20  # user units, see D6
LANDMARK_LABEL_SIZE = 15
CELL_WIDTH = 72
CELL_HEIGHT = 80
COLUMN_X = {1: 12, 2: 88, 3: 164, 4: 240, 5: 316}
ROW_Y = {"N": 12, "S": 148}

LABEL_PADDING = 8  # user units on each side of a label
LABEL_CHAR_EM_NUM = 13  # estimated glyph width = 0.65 em (generous for Cyrillic)
LABEL_CHAR_EM_DEN = 20


def estimated_label_width(label: str, size: int) -> int:
    return (len(label) * LABEL_CHAR_EM_NUM * size + LABEL_CHAR_EM_DEN - 1) // LABEL_CHAR_EM_DEN


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


OUTLINE = Rect(4, 4, 392, 232)
CORRIDOR = Rect(12, 96, 376, 48)


def label_text_length(label: str, rect: Rect, size: int) -> int | None:
    available = rect.width - 2 * LABEL_PADDING
    return available if estimated_label_width(label, size) > available else None


@dataclass(frozen=True)
class MapShape:
    kind: str  # "room" | "landmark"
    label: str  # room number or landmark label
    rect: Rect
    is_current: bool = False
    text_length: int | None = None


@dataclass(frozen=True)
class FloorPlan:
    floor: int
    width: int
    height: int
    outline: Rect
    corridor: Rect
    shapes: list[MapShape]


def cell_rect(cell: str) -> Rect:
    row, col = cell[0], int(cell[1:])
    return Rect(COLUMN_X[col], ROW_Y[row], CELL_WIDTH, CELL_HEIGHT)


def span_rect(cells: Sequence[str]) -> Rect:
    rects = [cell_rect(c) for c in cells]
    x = min(r.x for r in rects)
    y = rects[0].y
    width = max(r.x + r.width for r in rects) - x
    return Rect(x, y, width, CELL_HEIGHT)


def floor_plan(floor: int, rooms: Sequence[Room], current: Room | None) -> FloorPlan:
    blocked = blocked_cells(floor)
    landmark_shapes = [
        MapShape(
            "landmark",
            lm.label,
            (rect := span_rect(lm.cells)),
            text_length=label_text_length(lm.label, rect, LANDMARK_LABEL_SIZE),
        )
        for lm in landmarks_on(floor)
    ]
    room_shapes = [
        MapShape(
            "room",
            room.number,
            cell_rect(room.map_cell),
            is_current=current is not None and room.pk == current.pk,
        )
        for room in rooms
        if room.floor == floor and room.map_cell and room.map_cell not in blocked
    ]
    return FloorPlan(
        floor, VIEWBOX_WIDTH, VIEWBOX_HEIGHT, OUTLINE, CORRIDOR, landmark_shapes + room_shapes
    )
