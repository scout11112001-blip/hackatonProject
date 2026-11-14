"""Business rules for the schedule, called from mutations and admin forms."""

from collections.abc import Collection
from datetime import date, timedelta

from . import locking
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
    locking.lock_rooms_and_groups([room_id], group_ids)
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

    if not errors:
        errors.extend(
            _occurrence_conflicts(
                lesson_pk=exclude_pk,
                weekday=weekday,
                slot=slot,
                valid_from=valid_from,
                valid_until=valid_until,
                room_id=room_id,
                group_ids=group_ids,
            )
        )

    return errors


def _occurrence_conflicts(
    *,
    lesson_pk: int | None,
    weekday: int,
    slot: int,
    valid_from: date,
    valid_until: date,
    room_id: int,
    group_ids: Collection[int],
) -> list[str]:
    own_changes = (
        {
            c.original_date: c
            for c in LessonChange.objects.filter(weekly_lesson_id=lesson_pk).select_related(
                "new_room"
            )
        }
        if lesson_pk
        else {}
    )

    # Proposed own occurrences P: (date, slot_number, room_id, original_date).
    p: list[tuple[date, int, int | None, date]] = []
    d = valid_from
    while d <= valid_until:
        if d.weekday() == weekday:
            c = own_changes.get(d)
            if c is None:
                p.append((d, slot, room_id, d))
            elif c.kind == ChangeKind.ROOM_CHANGED:
                p.append((d, slot, c.new_room_id, d))
            # CANCELLED or MOVED: the regular occurrence is skipped.
        d += timedelta(days=1)

    for c in own_changes.values():
        if c.kind == ChangeKind.MOVED:
            p.append((c.new_date, c.new_slot, c.new_room_id or room_id, c.original_date))

    if not p:
        return []

    min_date = min(entry[0] for entry in p)
    max_date = max(entry[0] for entry in p)
    others = [
        i
        for i in occurrences_between(min_date, max_date, None)
        if i.is_happening and i.lesson.id != lesson_pk
    ]
    index: dict[tuple[date, int], list] = {}
    for item in others:
        index.setdefault((item.date, item.slot.number), []).append(item)

    errors: list[str] = []

    # Conflicts with other lessons' occurrences at the proposed date/slot.
    for p_date, p_slot, p_room, _ in p:
        for item in index.get((p_date, p_slot), []):
            if item.room.id == p_room:
                errors.append(
                    f"{p_date:%d.%m.%Y}, {p_slot} пара: аудитория {item.room.number} занята "
                    f"({item.lesson.discipline.name})."
                )
            for g in item.lesson.groups.all():
                if g.id in group_ids:
                    errors.append(
                        f"{p_date:%d.%m.%Y}, {p_slot} пара: группа {g.name} занята "
                        f"({item.lesson.discipline.name})."
                    )

    # Own duplicates: the same (date, slot) proposed twice (a move onto its own slot).
    seen: set[tuple[date, int]] = set()
    for p_date, p_slot, _room, _orig in p:
        key = (p_date, p_slot)
        if key in seen:
            errors.append(f"{p_date:%d.%m.%Y}, {p_slot} пара: занятие стоит дважды из-за переноса.")
        seen.add(key)

    # Own ROOM_CHANGED whose new room equals the lesson's (now) room.
    for c in own_changes.values():
        if c.kind == ChangeKind.ROOM_CHANGED and c.new_room_id == room_id:
            errors.append(
                f"Изменение на {c.original_date:%d.%m.%Y}: новая аудитория совпадает с аудиторией "
                "занятия. Удалите изменение."
            )

    deduped: list[str] = []
    seen_set: set[str] = set()
    for msg in errors:
        if msg not in seen_set:
            seen_set.add(msg)
            deduped.append(msg)

    if len(deduped) > 10:
        deduped = deduped[:10] + [f"…и ещё {len(deduped) - 10} конфликтов."]
    return deduped


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

    locking.lock_rooms_and_groups([target_room_id], group_ids)

    items = occurrences_between(target_date, target_date, None)
    conflicts: list[str] = []
    for item in items:
        if not item.is_happening or item.slot.number != target_slot:
            continue
        if item.lesson.id == lesson.id and item.original_date == change.original_date:
            continue
        if change.pk is not None and item.change is not None and item.change.pk == change.pk:
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


def restored_occurrence_conflicts(
    change: LessonChange, prefix: str = "Нельзя удалить изменение"
) -> list[str]:
    """Conflicts when ``change`` is removed and its original occurrence becomes regular again."""
    if change.kind == ChangeKind.TEACHER_REPLACED:
        return []

    lesson = change.weekly_lesson
    group_ids = set(lesson.groups.values_list("id", flat=True))

    locking.lock_rooms_and_groups([lesson.room_id], group_ids)

    items = occurrences_between(change.original_date, change.original_date, None)
    conflicts: list[str] = []
    for item in items:
        if not item.is_happening or item.slot.number != lesson.slot:
            continue
        if item.lesson.id == lesson.id and item.original_date == change.original_date:
            continue
        if item.room.id == lesson.room_id:
            conflicts.append(
                f"{prefix}: {change.original_date:%d.%m.%Y}, {lesson.slot} пара, "
                f"аудитория {item.room.number} уже занята ({item.lesson.discipline.name})."
            )
        for g in item.lesson.groups.all():
            if g.id in group_ids:
                conflicts.append(
                    f"{prefix}: {change.original_date:%d.%m.%Y}, "
                    f"{lesson.slot} пара, группа {g.name} уже занята "
                    f"({item.lesson.discipline.name})."
                )
    return conflicts


def released_occurrence_errors(old: LessonChange, new: LessonChange) -> list[str]:
    """Conflicts when an edit releases the old occurrence, and delete guards on identity change."""
    identity_changed = (
        old.weekly_lesson_id != new.weekly_lesson_id or old.original_date != new.original_date
    )
    hides = old.kind in (ChangeKind.CANCELLED, ChangeKind.MOVED, ChangeKind.ROOM_CHANGED)
    restores = hides and (identity_changed or new.kind == ChangeKind.TEACHER_REPLACED)
    if not restores and not identity_changed:
        return []

    rooms = {old.weekly_lesson.room_id, new.weekly_lesson.room_id, new.new_room_id}
    groups = set(old.weekly_lesson.groups.values_list("id", flat=True)) | set(
        new.weekly_lesson.groups.values_list("id", flat=True)
    )
    locking.lock_rooms_and_groups(rooms, groups)

    errors: list[str] = []
    if restores:
        errors += restored_occurrence_conflicts(old, prefix="Нельзя так изменить запись")
    if identity_changed:
        from .guards import run_change_guards

        errors += run_change_guards(old, deleting=True)
    return errors
