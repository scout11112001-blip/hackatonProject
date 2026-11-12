"""Business rules for the schedule, called from mutations and admin forms."""

from collections.abc import Collection
from datetime import date

from .models import ChangeKind, LessonChange, WeeklyLesson
from .services import occurrences_between


def validate_weekly_lesson(
    *,
    weekday: int,
    slot: int,
    valid_from: date,
    valid_until: date,
    room_id: int,
    group_ids: Collection[int],
    exclude_pk: int | None,
) -> list[str]:
    errors: list[str] = []
    if not group_ids:
        errors.append("Выберите хотя бы одну группу.")

    others = WeeklyLesson.objects.filter(
        weekday=weekday,
        slot=slot,
        valid_from__lte=valid_until,
        valid_until__gte=valid_from,
    )
    if exclude_pk is not None:
        others = others.exclude(pk=exclude_pk)

    for o in others.filter(room_id=room_id).select_related("discipline", "room"):
        errors.append(f"Аудитория {o.room.number} уже занята в это время: {o.discipline.name}.")

    for o in (
        others.filter(groups__in=group_ids)
        .distinct()
        .select_related("discipline")
        .prefetch_related("groups")
    ):
        for g in o.groups.all():
            if g.id in group_ids:
                errors.append(f"Группа {g.name} уже занята в это время: {o.discipline.name}.")

    if exclude_pk is not None:
        for c in LessonChange.objects.filter(weekly_lesson_id=exclude_pk):
            if c.original_date.weekday() != weekday or not (
                valid_from <= c.original_date <= valid_until
            ):
                errors.append(
                    f"Есть изменение на {c.original_date:%d.%m.%Y}, которое не подходит к новому "
                    "расписанию. Сначала удалите его."
                )

    return errors


def change_conflicts(change: LessonChange) -> list[str]:
    if change.kind in (ChangeKind.CANCELLED, ChangeKind.TEACHER_REPLACED):
        return []

    lesson = change.weekly_lesson
    if change.kind == ChangeKind.MOVED:
        target_date = change.new_date
        target_slot = change.new_slot
    else:  # ROOM_CHANGED
        target_date = change.original_date
        target_slot = lesson.slot

    target_room_id = change.new_room_id or lesson.room_id
    group_ids = set(lesson.groups.values_list("id", flat=True))

    items = occurrences_between(target_date, target_date, None)
    conflicts: list[str] = []
    for item in items:
        if not item.is_happening or item.slot.number != target_slot:
            continue
        if item.lesson.id == lesson.id and item.original_date == change.original_date:
            continue
        if item.room.id == target_room_id:
            conflicts.append(
                f"Аудитория {item.room.number} занята: {item.lesson.discipline.name}, "
                f"{target_date:%d.%m.%Y}, {target_slot} пара."
            )
        for g in item.lesson.groups.all():
            if g.id in group_ids:
                conflicts.append(
                    f"Группа {g.name} занята: {item.lesson.discipline.name}, "
                    f"{target_date:%d.%m.%Y}, {target_slot} пара."
                )
    return conflicts
