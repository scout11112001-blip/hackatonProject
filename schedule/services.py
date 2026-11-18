"""Read side of the schedule: occurrence computation and view helpers."""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum

from django.db.models import Q, QuerySet
from django.utils import timezone

from university.models import Room, Teacher

from .models import ChangeKind, LessonChange, WeeklyLesson
from .timeslots import TimeSlot, get_slot


class ItemKind(StrEnum):
    REGULAR = "regular"
    CANCELLED = "cancelled"
    MOVED_OUT = "moved-out"
    MOVED_IN = "moved-in"
    ROOM_CHANGED = "room-changed"
    TEACHER_REPLACED = "teacher-replaced"


@dataclass(frozen=True, eq=False)
class ScheduleItem:
    kind: ItemKind
    date: date
    slot: TimeSlot
    lesson: WeeklyLesson
    original_date: date
    room: Room
    teacher: Teacher
    original_room: Room | None = None
    original_teacher: Teacher | None = None
    change: LessonChange | None = None
    moved_to_date: date | None = None
    moved_to_slot: TimeSlot | None = None
    moved_from_date: date | None = None
    moved_from_slot: TimeSlot | None = None

    @property
    def is_happening(self) -> bool:
        return self.kind not in (ItemKind.CANCELLED, ItemKind.MOVED_OUT)

    @property
    def is_changed(self) -> bool:
        return self.kind != ItemKind.REGULAR


@dataclass(frozen=True)
class DaySchedule:
    date: date
    items: list[ScheduleItem]
    is_today: bool


@dataclass(frozen=True)
class WeekSchedule:
    start: date
    end: date
    days: list[DaySchedule]


@dataclass(frozen=True)
class TodayRow:
    item: ScheduleItem
    is_in_progress: bool
    is_next: bool


@dataclass(frozen=True)
class TodayAnnotation:
    rows: list[TodayRow]
    in_progress: ScheduleItem | None
    next_item: ScheduleItem | None
    day_finished: bool


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def changes_for_groups_between(
    group_ids: Collection[int] | None, start: date, end: date
) -> QuerySet[LessonChange]:
    qs = LessonChange.objects.filter(
        Q(original_date__range=(start, end))
        | Q(kind=ChangeKind.MOVED, new_date__range=(start, end))
    )
    if group_ids is not None:
        qs = qs.filter(weekly_lesson__groups__in=group_ids).distinct()
    return qs.select_related(
        "weekly_lesson__discipline",
        "weekly_lesson__teacher",
        "weekly_lesson__room",
        "new_room",
        "new_teacher",
    ).prefetch_related("weekly_lesson__groups")


def occurrences_between(
    start: date, end: date, group_ids: Collection[int] | None
) -> list[ScheduleItem]:
    if start > end:
        raise ValueError("start must not be after end")
    if group_ids is not None and not group_ids:
        return []

    lessons_qs = WeeklyLesson.objects.filter(valid_from__lte=end, valid_until__gte=start)
    if group_ids is not None:
        lessons_qs = lessons_qs.filter(groups__in=group_ids).distinct()
    lessons = list(
        lessons_qs.select_related("discipline", "teacher", "room").prefetch_related("groups")
    )

    changes = list(changes_for_groups_between(group_ids, start, end))
    by_key = {(c.weekly_lesson_id, c.original_date): c for c in changes}

    items: list[ScheduleItem] = []
    day = start
    while day <= end:
        for lesson in lessons:
            if lesson.weekday != day.weekday():
                continue
            if not lesson.valid_from <= day <= lesson.valid_until:
                continue
            change = by_key.get((lesson.id, day))
            if change is None:
                items.append(
                    ScheduleItem(
                        kind=ItemKind.REGULAR,
                        date=day,
                        slot=lesson.time_slot,
                        lesson=lesson,
                        original_date=day,
                        room=lesson.room,
                        teacher=lesson.teacher,
                    )
                )
            elif change.kind == ChangeKind.CANCELLED:
                items.append(
                    ScheduleItem(
                        kind=ItemKind.CANCELLED,
                        date=day,
                        slot=lesson.time_slot,
                        lesson=lesson,
                        original_date=day,
                        room=lesson.room,
                        teacher=lesson.teacher,
                        change=change,
                    )
                )
            elif change.kind == ChangeKind.MOVED:
                items.append(
                    ScheduleItem(
                        kind=ItemKind.MOVED_OUT,
                        date=day,
                        slot=lesson.time_slot,
                        lesson=lesson,
                        original_date=day,
                        room=lesson.room,
                        teacher=lesson.teacher,
                        change=change,
                        moved_to_date=change.new_date,
                        moved_to_slot=get_slot(change.new_slot),
                    )
                )
            elif change.kind == ChangeKind.ROOM_CHANGED:
                items.append(
                    ScheduleItem(
                        kind=ItemKind.ROOM_CHANGED,
                        date=day,
                        slot=lesson.time_slot,
                        lesson=lesson,
                        original_date=day,
                        room=change.new_room,
                        teacher=lesson.teacher,
                        original_room=lesson.room,
                        change=change,
                    )
                )
            elif change.kind == ChangeKind.TEACHER_REPLACED:
                items.append(
                    ScheduleItem(
                        kind=ItemKind.TEACHER_REPLACED,
                        date=day,
                        slot=lesson.time_slot,
                        lesson=lesson,
                        original_date=day,
                        room=lesson.room,
                        teacher=change.new_teacher,
                        original_teacher=lesson.teacher,
                        change=change,
                    )
                )
        day += timedelta(days=1)

    for change in changes:
        if change.kind != ChangeKind.MOVED:
            continue
        if not start <= change.new_date <= end:
            continue
        lesson = change.weekly_lesson
        has_new_room = change.new_room_id is not None and change.new_room_id != lesson.room_id
        items.append(
            ScheduleItem(
                kind=ItemKind.MOVED_IN,
                date=change.new_date,
                slot=get_slot(change.new_slot),
                lesson=lesson,
                original_date=change.original_date,
                room=change.new_room or lesson.room,
                teacher=lesson.teacher,
                original_room=lesson.room if has_new_room else None,
                change=change,
                moved_from_date=change.original_date,
                moved_from_slot=lesson.time_slot,
            )
        )

    items.sort(
        key=lambda i: (
            i.date,
            i.slot.number,
            i.is_happening is False,
            i.lesson.discipline.name,
        )
    )
    return items


def day_schedule(day: date, group_ids: Collection[int], today: date) -> DaySchedule:
    items = occurrences_between(day, day, group_ids)
    return DaySchedule(date=day, items=items, is_today=(day == today))


def week_schedule(any_day: date, group_ids: Collection[int], today: date) -> WeekSchedule:
    start = week_start(any_day)
    end = start + timedelta(days=6)
    items = occurrences_between(start, end, group_ids)
    by_date: dict[date, list[ScheduleItem]] = {}
    for item in items:
        by_date.setdefault(item.date, []).append(item)
    days = []
    day = start
    for _ in range(7):
        days.append(DaySchedule(date=day, items=by_date.get(day, []), is_today=(day == today)))
        day += timedelta(days=1)
    return WeekSchedule(start=start, end=end, days=days)


def annotate_today(items: list[ScheduleItem], now: time) -> TodayAnnotation:
    happening = [i for i in items if i.is_happening]
    in_progress = next((i for i in happening if i.slot.start <= now < i.slot.end), None)
    next_item = next((i for i in happening if i.slot.start > now), None)
    day_finished = bool(happening) and all(i.slot.end <= now for i in happening)
    rows = [
        TodayRow(item=i, is_in_progress=(i is in_progress), is_next=(i is next_item)) for i in items
    ]
    return TodayAnnotation(
        rows=rows,
        in_progress=in_progress,
        next_item=next_item,
        day_finished=day_finished,
    )


def today_schedule(group_id: int, now: datetime) -> tuple[DaySchedule, TodayAnnotation]:
    local = timezone.localtime(now)
    day = day_schedule(local.date(), [group_id], today=local.date())
    return day, annotate_today(day.items, local.time())
