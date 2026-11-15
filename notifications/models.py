import uuid

from django.conf import settings
from django.db import models

from core.clock import now

from .constants import BODY_MAX_LENGTH, TITLE_MAX_LENGTH


class Audience(models.TextChoices):
    UNIVERSITY = "university", "Весь университет"
    FACULTY = "faculty", "Факультет"
    GROUP = "group", "Группа"


class Announcement(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField("заголовок", max_length=TITLE_MAX_LENGTH)
    body = models.TextField("текст", max_length=BODY_MAX_LENGTH)
    audience = models.CharField("кому", max_length=16, choices=Audience.choices)
    faculty = models.ForeignKey(
        "university.Faculty",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="announcements",
        verbose_name="факультет",
    )
    group = models.ForeignKey(
        "university.StudyGroup",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="announcements",
        verbose_name="группа",
    )
    deadline = models.DateField("срок (включительно)", null=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="announcements",
        verbose_name="автор",
    )
    published_at = models.DateTimeField("опубликовано", default=now, editable=False)
    is_published = models.BooleanField("опубликовано", default=True)
    unpublished_at = models.DateTimeField(
        "снято с публикации", null=True, blank=True, editable=False
    )
    unpublished_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
        verbose_name="снял с публикации",
    )
    seed_key = models.SlugField(max_length=40, blank=True, default="", editable=False)

    class Meta:
        ordering = ["-published_at", "-pk"]
        indexes = [
            models.Index(fields=["is_published", "published_at"], name="notif_ann_published_idx"),
            models.Index(fields=["deadline"], name="notif_ann_deadline_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                name="notifications_announcement_audience_target",
                condition=(
                    models.Q(audience="university", faculty__isnull=True, group__isnull=True)
                    | models.Q(audience="faculty", faculty__isnull=False, group__isnull=True)
                    | models.Q(audience="group", faculty__isnull=True, group__isnull=False)
                ),
                violation_error_message=(
                    "Получатели не соответствуют аудитории: для всего университета не выбирайте "
                    "ни факультет, ни группу; для факультета выберите только факультет; "
                    "для группы выберите только группу."
                ),
            ),
            models.CheckConstraint(
                condition=~models.Q(title=""), name="notifications_announcement_title_not_empty"
            ),
            models.CheckConstraint(
                condition=~models.Q(body=""), name="notifications_announcement_body_not_empty"
            ),
            models.CheckConstraint(
                condition=models.Q(audience__in=["university", "faculty", "group"]),
                name="notifications_announcement_audience_value",
            ),
            models.UniqueConstraint(
                fields=["seed_key"],
                condition=~models.Q(seed_key=""),
                name="notifications_announcement_unique_seed_key",
            ),
        ]
        verbose_name = "объявление"
        verbose_name_plural = "объявления"

    def __str__(self) -> str:
        return self.title

    @property
    def audience_label(self) -> str:
        if self.audience == Audience.UNIVERSITY:
            return "Для всех студентов"
        if self.audience == Audience.FACULTY:
            return self.faculty.name
        return f"Группа {self.group.name}"


class NotificationState(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_state",
        verbose_name="пользователь",
    )
    seen_until = models.DateTimeField("просмотрено до", null=True, blank=True)

    class Meta:
        verbose_name = "состояние уведомлений"
        verbose_name_plural = "состояния уведомлений"

    def __str__(self) -> str:
        return f"{self.user_id}: {self.seen_until}"
