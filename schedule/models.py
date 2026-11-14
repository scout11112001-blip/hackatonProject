from django.core.exceptions import ValidationError
from django.db import models

from .timeslots import MAX_SLOT, SLOT_CHOICES, get_slot


class Weekday(models.IntegerChoices):
    MONDAY = 0, "Понедельник"
    TUESDAY = 1, "Вторник"
    WEDNESDAY = 2, "Среда"
    THURSDAY = 3, "Четверг"
    FRIDAY = 4, "Пятница"
    SATURDAY = 5, "Суббота"
    SUNDAY = 6, "Воскресенье"


class LessonType(models.TextChoices):
    LECTURE = "lecture", "Лекция"
    SEMINAR = "seminar", "Семинар"
    LAB = "lab", "Лабораторная работа"


class ChangeKind(models.TextChoices):
    CANCELLED = "cancelled", "Отмена"
    MOVED = "moved", "Перенос"
    ROOM_CHANGED = "room_changed", "Замена аудитории"
    TEACHER_REPLACED = "teacher_replaced", "Замена преподавателя"


class WeeklyLesson(models.Model):
    weekday = models.PositiveSmallIntegerField("день недели", choices=Weekday.choices)
    slot = models.PositiveSmallIntegerField("пара", choices=SLOT_CHOICES)
    discipline = models.ForeignKey(
        "university.Discipline",
        on_delete=models.PROTECT,
        related_name="weekly_lessons",
        verbose_name="дисциплина",
    )
    lesson_type = models.CharField("тип занятия", max_length=16, choices=LessonType.choices)
    teacher = models.ForeignKey(
        "university.Teacher",
        on_delete=models.PROTECT,
        related_name="weekly_lessons",
        verbose_name="преподаватель",
    )
    room = models.ForeignKey(
        "university.Room",
        on_delete=models.PROTECT,
        related_name="weekly_lessons",
        verbose_name="аудитория",
    )
    groups = models.ManyToManyField(
        "university.StudyGroup", related_name="weekly_lessons", verbose_name="группы"
    )
    valid_from = models.DateField("действует с")
    valid_until = models.DateField("действует по")
    seed_key = models.SlugField(
        "ключ демо-данных", max_length=40, blank=True, default="", editable=False
    )

    class Meta:
        ordering = ["weekday", "slot"]
        indexes = [models.Index(fields=["weekday", "slot"], name="schedule_weekly_day_slot_idx")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valid_until__gte=models.F("valid_from")),
                name="schedule_weekly_valid_range",
            ),
            models.CheckConstraint(
                condition=models.Q(weekday__gte=0) & models.Q(weekday__lte=6),
                name="schedule_weekly_weekday_0_6",
            ),
            models.CheckConstraint(
                condition=models.Q(slot__gte=1) & models.Q(slot__lte=MAX_SLOT),
                name="schedule_weekly_slot_range",
            ),
            models.UniqueConstraint(
                fields=["seed_key"],
                condition=~models.Q(seed_key=""),
                name="schedule_weekly_unique_seed_key",
            ),
        ]
        verbose_name = "занятие (еженедельное)"
        verbose_name_plural = "занятия (еженедельные)"

    def __str__(self) -> str:
        return f"{self.get_weekday_display()}, {self.slot} пара — {self.discipline}"

    def clean(self):
        super().clean()
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValidationError({"valid_until": "Дата окончания раньше даты начала."})

    @property
    def time_slot(self):
        return get_slot(self.slot)


class LessonChange(models.Model):
    weekly_lesson = models.ForeignKey(
        WeeklyLesson,
        on_delete=models.CASCADE,
        related_name="changes",
        verbose_name="занятие",
    )
    original_date = models.DateField("дата занятия по расписанию")
    kind = models.CharField("вид изменения", max_length=20, choices=ChangeKind.choices)
    new_date = models.DateField("новая дата", null=True, blank=True)
    new_slot = models.PositiveSmallIntegerField(
        "новая пара", choices=SLOT_CHOICES, null=True, blank=True
    )
    new_room = models.ForeignKey(
        "university.Room",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="новая аудитория",
    )
    new_teacher = models.ForeignKey(
        "university.Teacher",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="новый преподаватель",
    )
    reason = models.CharField("причина", max_length=200)
    created_at = models.DateTimeField("создано", auto_now_add=True)
    seed_key = models.SlugField(
        "ключ демо-данных", max_length=40, blank=True, default="", editable=False
    )

    class Meta:
        ordering = ["original_date"]
        indexes = [
            models.Index(fields=["original_date"], name="schedule_change_orig_idx"),
            models.Index(fields=["new_date"], name="schedule_change_new_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["weekly_lesson", "original_date"],
                name="schedule_change_one_per_occurrence",
            ),
            models.CheckConstraint(
                condition=~models.Q(reason=""), name="schedule_change_reason_required"
            ),
            models.UniqueConstraint(
                fields=["seed_key"],
                condition=~models.Q(seed_key=""),
                name="schedule_change_unique_seed_key",
            ),
            models.CheckConstraint(
                name="schedule_change_fields_match_kind",
                condition=(
                    models.Q(
                        kind="cancelled",
                        new_date__isnull=True,
                        new_slot__isnull=True,
                        new_room__isnull=True,
                        new_teacher__isnull=True,
                    )
                    | models.Q(
                        kind="moved",
                        new_date__isnull=False,
                        new_slot__isnull=False,
                        new_teacher__isnull=True,
                    )
                    | models.Q(
                        kind="room_changed",
                        new_room__isnull=False,
                        new_date__isnull=True,
                        new_slot__isnull=True,
                        new_teacher__isnull=True,
                    )
                    | models.Q(
                        kind="teacher_replaced",
                        new_teacher__isnull=False,
                        new_date__isnull=True,
                        new_slot__isnull=True,
                        new_room__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(
                condition=models.Q(new_slot__isnull=True)
                | (models.Q(new_slot__gte=1) & models.Q(new_slot__lte=MAX_SLOT)),
                name="schedule_change_new_slot_range",
            ),
        ]
        verbose_name = "изменение расписания"
        verbose_name_plural = "изменения расписания"

    def __str__(self) -> str:
        return f"{self.get_kind_display()}: {self.weekly_lesson} ({self.original_date:%d.%m.%Y})"

    def clean(self):
        super().clean()
        if self.weekly_lesson_id is None or self.original_date is None or not self.kind:
            return
        lesson = self.weekly_lesson
        errors: dict[str, list[str]] = {}
        if self.original_date.weekday() != lesson.weekday:
            errors.setdefault("original_date", []).append(
                "Дата не совпадает с днём недели занятия."
            )
        if not lesson.valid_from <= self.original_date <= lesson.valid_until:
            errors.setdefault("original_date", []).append("Дата вне периода действия занятия.")

        # Kind rules (mirror of the DB constraint, field-level messages).
        required = {
            ChangeKind.MOVED: ("new_date", "new_slot"),
            ChangeKind.ROOM_CHANGED: ("new_room",),
            ChangeKind.TEACHER_REPLACED: ("new_teacher",),
        }
        for field in required.get(self.kind, ()):
            if getattr(self, field) is None:
                errors.setdefault(field, []).append("Обязательно для этого вида изменения.")

        forbidden = {
            ChangeKind.CANCELLED: ("new_date", "new_slot", "new_room", "new_teacher"),
            ChangeKind.MOVED: ("new_teacher",),
            ChangeKind.ROOM_CHANGED: ("new_date", "new_slot", "new_teacher"),
            ChangeKind.TEACHER_REPLACED: ("new_date", "new_slot", "new_room"),
        }
        for field in forbidden.get(self.kind, ()):
            if getattr(self, field) is not None:
                errors.setdefault(field, []).append("Не заполняйте для этого вида изменения.")

        if self.kind == ChangeKind.MOVED:
            if (self.new_date, self.new_slot) == (self.original_date, lesson.slot) and (
                self.new_room is None or self.new_room_id == lesson.room_id
            ):
                errors.setdefault("new_date", []).append("Новое время совпадает со старым.")
        elif self.kind == ChangeKind.ROOM_CHANGED:
            if self.new_room_id == lesson.room_id:
                errors.setdefault("new_room", []).append("Аудитория не изменилась.")
        elif self.kind == ChangeKind.TEACHER_REPLACED:
            if self.new_teacher_id == lesson.teacher_id:
                errors.setdefault("new_teacher", []).append("Преподаватель не изменился.")

        if errors:
            raise ValidationError(errors)

        if self.pk is not None:
            old = LessonChange.objects.select_related("weekly_lesson").filter(pk=self.pk).first()
            if old is not None:
                from .validation import released_occurrence_errors

                released = released_occurrence_errors(old, self)
                if released:
                    raise ValidationError(released)

        from .guards import run_change_guards

        guard_errors = run_change_guards(self, deleting=False)
        if guard_errors:
            raise ValidationError(guard_errors)

        from .validation import change_conflicts

        conflicts = change_conflicts(self)
        if conflicts:
            raise ValidationError(conflicts)
