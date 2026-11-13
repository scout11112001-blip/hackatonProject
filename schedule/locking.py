"""Serialize schedule writes by locking the rooms and groups they touch.

Any two conflicting lessons/changes share a room or a group, so locking those
rows makes the second writer wait until the first commits; its conflict queries
then see the committed data (PostgreSQL READ COMMITTED takes a new snapshot per
statement). On SQLite Django ignores ``select_for_update()`` (no ``FOR UPDATE``
support); SQLite serializes writers with a database-level lock anyway.
"""

from collections.abc import Iterable

from django.db import transaction

from university.models import Room, StudyGroup


def lock_rooms_and_groups(room_ids: Iterable[int | None], group_ids: Iterable[int]) -> None:
    if not transaction.get_connection().in_atomic_block:
        return
    rooms = sorted({r for r in room_ids if r is not None})
    groups = sorted(set(group_ids))
    if rooms:
        list(
            Room.objects.select_for_update()
            .filter(pk__in=rooms)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
    if groups:
        list(
            StudyGroup.objects.select_for_update()
            .filter(pk__in=groups)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
