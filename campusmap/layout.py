"""Geometry for the schematic building plan. All values are integers."""

from dataclasses import dataclass

from university.building import (
    CORRIDOR,
    OUTLINE,
    ROOM,
    VIEWBOX_HEIGHT,
    VIEWBOX_WIDTH,
    Rect,
    Space,
    plan_for,
)
from university.models import Room

ROOM_LABEL_SIZE = 20  # user units, see D6
LANDMARK_LABEL_SIZE = 15

LABEL_PADDING = 8  # user units on each side of a label
LABEL_CHAR_EM_NUM = 13  # estimated glyph width = 0.65 em (generous for Cyrillic)
LABEL_CHAR_EM_DEN = 20


def estimated_label_width(label: str, size: int) -> int:
    return (len(label) * LABEL_CHAR_EM_NUM * size + LABEL_CHAR_EM_DEN - 1) // LABEL_CHAR_EM_DEN


def label_text_length(label: str, rect: Rect, size: int) -> int | None:
    available = rect.width - 2 * LABEL_PADDING
    return available if estimated_label_width(label, size) > available else None


@dataclass(frozen=True)
class MapShape:
    kind: str  # "room" | "landmark" | "service"
    label: str  # room number or landmark/service label
    rect: Rect  # label rectangle (parts[0]); also the drawn rectangle for one-part spaces
    points: str = ""  # SVG points attribute for polygons
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


def svg_points(points: tuple[tuple[int, int], ...]) -> str:
    return " ".join(f"{x},{y}" for x, y in points)


def label_size(kind: str) -> int:
    return ROOM_LABEL_SIZE if kind == ROOM else LANDMARK_LABEL_SIZE


def floor_plan(floor: int, current: Room | None) -> FloorPlan | None:
    spaces: tuple[Space, ...] | None = plan_for(floor)
    if spaces is None:
        return None
    shapes = []
    for space in spaces:
        rect = space.parts[0]
        shapes.append(
            MapShape(
                kind=space.kind,
                label=space.label,
                rect=rect,
                points=svg_points(space.points),
                is_current=(
                    space.kind == ROOM
                    and current is not None
                    and current.floor == floor
                    and current.number == space.label
                ),
                text_length=label_text_length(space.label, rect, label_size(space.kind)),
            )
        )
    return FloorPlan(floor, VIEWBOX_WIDTH, VIEWBOX_HEIGHT, OUTLINE, CORRIDOR, shapes)
