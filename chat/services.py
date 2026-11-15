"""Chat services: sending messages, read markers and history loading."""

from datetime import timedelta
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from accounts.access import get_profile_for_role
from accounts.models import StudentProfile, User
from core import clock

from .constants import (
    FRAGMENT_LIMIT,
    HISTORY_LIMIT,
    MESSAGE_MAX_LENGTH,
    RATE_LIMIT_MESSAGES,
    RATE_LIMIT_MINUTES,
)
from .models import AuthorRole, Dialog, Message
from .selectors import dialogs_visible_to


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def text_errors(text: str) -> list[str]:
    if not text:
        return ["Сообщение пустое."]
    if len(text) > MESSAGE_MAX_LENGTH:
        return [f"Сообщение длиннее {MESSAGE_MAX_LENGTH} символов."]
    return []


def _idempotent_message(dialog: Dialog, client_token: UUID | None) -> Message | None:
    if client_token is None:
        return None
    return dialog.messages.filter(client_token=client_token).first()


def send_student_message(student: StudentProfile, text: str, client_token: UUID | None) -> Message:
    text = normalize_text(text)
    errors = text_errors(text)
    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        dialog, _ = Dialog.objects.get_or_create(student=student)
        dialog = Dialog.objects.select_for_update().get(pk=dialog.pk)

        existing = _idempotent_message(dialog, client_token)
        if existing is not None:
            return existing

        now = clock.now()
        recent = Message.objects.filter(
            author_id=student.user_id,
            author_role=AuthorRole.STUDENT,
            created_at__gt=now - timedelta(minutes=RATE_LIMIT_MINUTES),
        ).count()
        if recent >= RATE_LIMIT_MESSAGES:
            raise ValidationError(
                f"Можно отправить не больше {RATE_LIMIT_MESSAGES} сообщений "
                f"за {RATE_LIMIT_MINUTES} минут. Подождите немного."
            )

        message = Message(
            dialog=dialog,
            author=student.user,
            author_role=AuthorRole.STUDENT,
            text=text,
            created_at=now,
            client_token=client_token,
        )
        message.full_clean()
        message.save()

        Dialog.objects.filter(pk=dialog.pk).update(last_message_at=now, last_message_id=message.pk)
        return message


def send_staff_message(
    dialog: Dialog, actor: User, text: str, client_token: UUID | None
) -> Message:
    get_profile_for_role(actor, User.Role.STAFF)
    text = normalize_text(text)
    errors = text_errors(text)
    if errors:
        raise ValidationError(errors)

    with transaction.atomic():
        locked = (
            dialogs_visible_to(actor).select_for_update(of=("self",)).filter(pk=dialog.pk).first()
        )
        if locked is None:
            raise PermissionDenied

        existing = _idempotent_message(locked, client_token)
        if existing is not None:
            return existing

        now = clock.now()
        message = Message(
            dialog=locked,
            author=actor,
            author_role=AuthorRole.STAFF,
            text=text,
            created_at=now,
            client_token=client_token,
        )
        message.full_clean()
        message.save()

        Dialog.objects.filter(pk=locked.pk).update(last_message_at=now, last_message_id=message.pk)
        return message


def mark_read(dialog_id: int, side: str, up_to_id: int) -> None:
    field = {"student": "student_read_id", "staff": "staff_read_id"}[side]
    if up_to_id <= 0:
        return
    Dialog.objects.filter(pk=dialog_id, **{f"{field}__lt": up_to_id}).update(**{field: up_to_id})


def load_history(dialog: Dialog) -> tuple[list[Message], bool]:
    rows = list(
        dialog.messages.select_related("author__staff_profile").order_by("-id")[: HISTORY_LIMIT + 1]
    )
    truncated = len(rows) > HISTORY_LIMIT
    return list(reversed(rows[:HISTORY_LIMIT])), truncated


def messages_after(dialog: Dialog, after_id: int) -> list[Message]:
    return list(
        dialog.messages.filter(id__gt=after_id)
        .select_related("author__staff_profile")
        .order_by("id")[:FRAGMENT_LIMIT]
    )
