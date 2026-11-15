"""Plain helper functions for schedule tests (no extra dependencies)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from schedule.models import WeeklyLesson
from schedule.mutations import save_weekly_lesson
from university.models import Discipline, Room, Teacher

MOSCOW = ZoneInfo("Europe/Moscow")

_counter = 0


def _next_counter() -> int:
    global _counter
    _counter += 1
    return _counter


def make_room(code: str, floor: int | None = None) -> Room:
    number = code.removeprefix("room-")
    if floor is None:
        floor = int(number[0])
    return Room.objects.create(code=code, floor=floor, number=number)


def make_teacher(last_name: str) -> Teacher:
    return Teacher.objects.create(last_name=last_name, first_name="Иван")


def make_discipline(name: str) -> Discipline:
    return Discipline.objects.create(name=name, short_name=name[:10])


def make_lesson(
    groups,
    weekday: int,
    slot: int,
    room: Room,
    *,
    discipline: Discipline | None = None,
    teacher: Teacher | None = None,
    lesson_type: str = "lecture",
    valid_from: date = date(2026, 9, 1),
    valid_until: date = date(2026, 12, 31),
) -> WeeklyLesson:
    if discipline is None:
        discipline = make_discipline(f"Дисциплина {_next_counter()}")
    if teacher is None:
        teacher = make_teacher(f"Преподаватель {_next_counter()}")
    lesson = WeeklyLesson(
        weekday=weekday,
        slot=slot,
        discipline=discipline,
        lesson_type=lesson_type,
        teacher=teacher,
        room=room,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    return save_weekly_lesson(lesson, list(groups))


def aware(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str).replace(tzinfo=MOSCOW)
