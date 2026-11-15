"""Announcement and read-state services."""

from datetime import date, datetime, timedelta
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.access import get_profile_for_role
from accounts.models import User
from accounts.selectors import groups_visible_to
from university.models import StudyGroup

from .constants import DEADLINE_MAX_DAYS_AHEAD
from .models import Announcement, Audience, NotificationState
from .selectors import announcements_managed_by


def deadline_errors(deadline: date | None, today: date) -> list[str]:
    if deadline is None:
        return []
    if deadline < today:
        return ["Срок не может быть в прошлом."]
    if deadline > today + timedelta(days=DEADLINE_MAX_DAYS_AHEAD):
        return [f"Срок — не позже чем через {DEADLINE_MAX_DAYS_AHEAD} дней."]
    return []


def create_announcement(
    author: User,
    *,
    title: str,
    body: str,
    audience: str,
    group: StudyGroup | None,
    deadline: date | None,
) -> Announcement:
    staff = get_profile_for_role(author, User.Role.STAFF)
    now = timezone.now()
    today = timezone.localdate(now)
    errors = deadline_errors(deadline, today)

    faculty = None
    target_group = None
    if audience == Audience.FACULTY:
        faculty = staff.faculty
    elif audience == Audience.GROUP:
        if group is None:
            errors.append("Выберите группу.")
        elif not groups_visible_to(author).filter(pk=group.pk).exists():
            errors.append("Группа не относится к вашему факультету.")
        target_group = group
    else:
        errors.append(
            "Сотрудник может адресовать объявление только своему факультету или его группе."
        )

    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        announcement = Announcement(
            title=title,
            body=body,
            audience=audience,
            faculty=faculty,
            group=target_group,
            deadline=deadline,
            author=author,
            published_at=now,
            is_published=True,
        )
        announcement.full_clean()
        announcement.save()
        return announcement


def unpublish_announcement(actor: User, public_id: UUID) -> bool:
    get_profile_for_role(actor, User.Role.STAFF)
    with transaction.atomic():
        ann = (
            announcements_managed_by(actor)
            .select_for_update(of=("self",))
            .filter(public_id=public_id)
            .first()
        )
        if ann is None:
            raise Announcement.DoesNotExist
        if not ann.is_published:
            return False
        ann.is_published = False
        ann.unpublished_at = timezone.now()
        ann.unpublished_by = actor
        ann.save(update_fields=["is_published", "unpublished_at", "unpublished_by"])
        return True


def mark_seen(user_id: int, now: datetime) -> None:
    updated = (
        NotificationState.objects.filter(user_id=user_id)
        .filter(Q(seen_until__isnull=True) | Q(seen_until__lt=now))
        .update(seen_until=now)
    )
    if updated == 0:
        NotificationState.objects.get_or_create(user_id=user_id, defaults={"seen_until": now})
