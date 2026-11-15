"""Test helpers for the chat app."""

from django.utils import timezone

from chat.models import Dialog, Message


def make_dialog(student_profile) -> Dialog:
    dialog, _ = Dialog.objects.get_or_create(student=student_profile)
    return dialog


def add_message(dialog, author, role, text="Текст", created_at=None) -> Message:
    created_at = created_at or timezone.now()
    message = Message.objects.create(
        dialog=dialog,
        author=author,
        author_role=role,
        text=text,
        created_at=created_at,
    )
    Dialog.objects.filter(pk=dialog.pk).update(
        last_message_at=created_at, last_message_id=message.pk
    )
    return message
