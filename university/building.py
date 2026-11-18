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


def plan_for(floor: int) -> tuple[Space, ...] | None:
    return FLOOR_PLANS.get(floor)


def plan_room_numbers(floor: int) -> frozenset[str]:
    return frozenset(s.label for s in FLOOR_PLANS.get(floor, ()) if s.kind == ROOM)


def all_plan_rooms() -> list[tuple[int, str]]:
    """(floor, number) of every room slot, ordered by floor and number."""
    return sorted(
        (floor, s.label) for floor, spaces in FLOOR_PLANS.items() for s in spaces if s.kind == ROOM
    )
