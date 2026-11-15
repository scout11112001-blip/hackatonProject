import uuid

from django.conf import settings
from django.db import models

from core import clock

from .constants import MESSAGE_MAX_LENGTH


class AuthorRole(models.TextChoices):
    STUDENT = "student", "Студент"
    STAFF = "staff", "Деканат"


class Dialog(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student = models.OneToOneField(
        "accounts.StudentProfile",
        on_delete=models.PROTECT,
        related_name="chat_dialog",
        verbose_name="студент",
    )
    created_at = models.DateTimeField("создан", default=clock.now, editable=False)
    last_message_at = models.DateTimeField(
        "последнее сообщение", null=True, blank=True, editable=False
    )
    last_message_id = models.PositiveBigIntegerField(default=0, editable=False)
    student_read_id = models.PositiveBigIntegerField(default=0, editable=False)
    staff_read_id = models.PositiveBigIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["-last_message_at", "-pk"]
        indexes = [models.Index(fields=["last_message_at"], name="chat_dialog_last_msg_idx")]
        verbose_name = "диалог"
        verbose_name_plural = "диалоги"

    def __str__(self) -> str:
        return f"Чат: {self.student}"


class Message(models.Model):
    dialog = models.ForeignKey(
        Dialog, on_delete=models.PROTECT, related_name="messages", verbose_name="диалог"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="chat_messages",
        verbose_name="автор",
    )
    author_role = models.CharField("роль автора", max_length=16, choices=AuthorRole.choices)
    text = models.TextField("текст", max_length=MESSAGE_MAX_LENGTH)
    created_at = models.DateTimeField("отправлено", default=clock.now, editable=False)
    client_token = models.UUIDField(null=True, blank=True, editable=False)
    seed_key = models.SlugField(max_length=40, blank=True, default="", editable=False)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["dialog", "id"], name="chat_msg_dialog_id_idx"),
            models.Index(fields=["author", "created_at"], name="chat_msg_author_time_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(text=""), name="chat_message_text_not_empty"
            ),
            models.CheckConstraint(
                condition=models.Q(author_role__in=["student", "staff"]),
                name="chat_message_author_role_value",
            ),
            models.UniqueConstraint(
                fields=["dialog", "client_token"],
                condition=models.Q(client_token__isnull=False),
                name="chat_message_unique_client_token",
            ),
            models.UniqueConstraint(
                fields=["seed_key"],
                condition=~models.Q(seed_key=""),
                name="chat_message_unique_seed_key",
            ),
        ]
        verbose_name = "сообщение"
        verbose_name_plural = "сообщения"

    def __str__(self) -> str:
        return f"{self.get_author_role_display()}: {self.text[:40]}"
