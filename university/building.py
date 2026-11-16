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
    kind: str  # ROOM | LANDMARK | SERVICE
    label: str  # room number NNN or a Russian name
    parts: tuple[Rect, ...]  # disjoint; parts[0] is the label rectangle
    points: tuple[tuple[int, int], ...] = ()  # polygon outline when len(parts) > 1


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
    return sorted(
        (floor, s.label) for floor, spaces in FLOOR_PLANS.items() for s in spaces if s.kind == ROOM
    )
