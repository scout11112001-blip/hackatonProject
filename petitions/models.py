"""Models for the petitions (requests for certificates and applications) app."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.clock import now
from core.storage import get_private_storage
from petitions.files import attachment_upload_to

MAX_COMMENT_LENGTH = 2000


class RequestKind(models.TextChoices):
    CERTIFICATE = "certificate", "Справка"
    APPLICATION = "application", "Заявление"


class PetitionStatus(models.TextChoices):
    SUBMITTED = "submitted", "Подана"
    IN_PROGRESS = "in_progress", "В работе"
    READY = "ready", "Готова"
    ISSUED = "issued", "Выдана"
    REJECTED = "rejected", "Отклонена"


STATUS_VALUES = [s.value for s in PetitionStatus]


class RequestType(models.Model):
    name = models.CharField("название", max_length=200, unique=True)
    kind = models.CharField("вид", max_length=16, choices=RequestKind.choices)
    description = models.TextField("описание", blank=True, default="")
    processing_days = models.PositiveSmallIntegerField(
        "срок, рабочих дней", validators=[MinValueValidator(1), MaxValueValidator(60)]
    )
    comment_required = models.BooleanField("комментарий обязателен", default=False)
    comment_hint = models.CharField(
        "подсказка к комментарию", max_length=255, blank=True, default=""
    )
    is_active = models.BooleanField("доступна для подачи", default=True)

    class Meta:
        ordering = ["kind", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(processing_days__gte=1) & models.Q(processing_days__lte=60),
                name="petitions_type_days_1_60",
            )
        ]
        verbose_name = "вид заявки"
        verbose_name_plural = "виды заявок"

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        if self.comment_required and not self.comment_hint:
            raise ValidationError("Для обязательного комментария заполните подсказку.")


class Petition(models.Model):
    public_id = models.UUIDField("номер", default=uuid.uuid4, unique=True, editable=False)
    student = models.ForeignKey(
        "accounts.StudentProfile",
        on_delete=models.PROTECT,
        related_name="petitions",
        verbose_name="студент",
    )
    request_type = models.ForeignKey(
        RequestType, on_delete=models.PROTECT, related_name="petitions", verbose_name="вид заявки"
    )
    comment = models.TextField("комментарий", blank=True, default="", max_length=MAX_COMMENT_LENGTH)
    status = models.CharField(
        "статус", max_length=16, choices=PetitionStatus.choices, default=PetitionStatus.SUBMITTED
    )
    created_at = models.DateTimeField("подана", default=now)
    status_changed_at = models.DateTimeField("статус изменён", default=now)
    expected_ready_date = models.DateField("ожидаемая дата готовности")
    seed_key = models.SlugField(max_length=40, blank=True, default="", editable=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="petitions_status_created_idx")
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=STATUS_VALUES), name="petitions_status_value"
            ),
            models.UniqueConstraint(
                fields=["seed_key"],
                condition=~models.Q(seed_key=""),
                name="petitions_unique_seed_key",
            ),
        ]
        verbose_name = "заявка"
        verbose_name_plural = "заявки"

    def __str__(self) -> str:
        return f"{self.request_type} — {self.student} ({self.get_status_display()})"

    @property
    def short_id(self) -> str:
        return str(self.public_id)[:8]


class PetitionAttachment(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    petition = models.ForeignKey(
        Petition, on_delete=models.CASCADE, related_name="attachments", verbose_name="заявка"
    )
    file = models.FileField(
        upload_to=attachment_upload_to, storage=get_private_storage, max_length=100, unique=True
    )
    original_name = models.CharField("имя файла", max_length=120)
    size = models.PositiveIntegerField("размер, байт")
    uploaded_at = models.DateTimeField(default=now)

    class Meta:
        ordering = ["uploaded_at", "pk"]
        verbose_name = "приложение к заявке"
        verbose_name_plural = "приложения к заявкам"

    def __str__(self) -> str:
        return self.original_name


class PetitionStatusChange(models.Model):
    petition = models.ForeignKey(
        Petition, on_delete=models.CASCADE, related_name="history", verbose_name="заявка"
    )
    from_status = models.CharField(
        max_length=16, choices=PetitionStatus.choices, blank=True, default=""
    )
    to_status = models.CharField(max_length=16, choices=PetitionStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="petition_status_changes",
        verbose_name="автор",
    )
    created_at = models.DateTimeField(default=now)
    comment = models.TextField(blank=True, default="", max_length=MAX_COMMENT_LENGTH)

    class Meta:
        ordering = ["created_at", "pk"]
        indexes = [models.Index(fields=["created_at"], name="petitions_history_created_idx")]
        verbose_name = "изменение статуса"
        verbose_name_plural = "изменения статуса"

    def __str__(self) -> str:
        return f"{self.petition_id} {self.from_status or '—'} → {self.to_status}"


class PetitionComment(models.Model):
    petition = models.ForeignKey(
        Petition, on_delete=models.CASCADE, related_name="staff_comments", verbose_name="заявка"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="petition_comments",
        verbose_name="автор",
    )
    created_at = models.DateTimeField(default=now)
    text = models.TextField(max_length=MAX_COMMENT_LENGTH)

    class Meta:
        ordering = ["created_at", "pk"]
        constraints = [
            models.CheckConstraint(condition=~models.Q(text=""), name="petitions_comment_not_empty")
        ]
        verbose_name = "комментарий сотрудника"
        verbose_name_plural = "комментарии сотрудников"

    def __str__(self) -> str:
        return f"{self.author} — {self.text[:50]}"
