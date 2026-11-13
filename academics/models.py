from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class AssessmentForm(models.TextChoices):
    EXAM = "exam", "Экзамен"
    CREDIT = "credit", "Зачёт"
    GRADED_CREDIT = "graded_credit", "Дифференцированный зачёт"


class ResultValue(models.TextChoices):
    FIVE = "5", "Отлично (5)"
    FOUR = "4", "Хорошо (4)"
    THREE = "3", "Удовлетворительно (3)"
    TWO = "2", "Неудовлетворительно (2)"
    PASS = "pass", "Зачтено"
    FAIL = "fail", "Не зачтено"


NUMERIC_RESULTS = {"5", "4", "3", "2"}
PASS_FAIL_RESULTS = {"pass", "fail"}
POSITIVE_RESULTS = {"5", "4", "3", "pass"}


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Присутствовал"
    ABSENT = "absent", "Отсутствовал"
    EXCUSED = "excused", "Уважительная причина"


class Term(models.Model):
    code = models.SlugField("код", max_length=30, unique=True)
    name = models.CharField("название", max_length=100)
    start_date = models.DateField("начало")
    end_date = models.DateField("окончание")
    session_start = models.DateField("начало сессии")
    session_end = models.DateField("окончание сессии")

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(start_date__lte=models.F("session_start"))
                & models.Q(session_start__lte=models.F("session_end"))
                & models.Q(session_end__lte=models.F("end_date")),
                name="academics_term_dates_order",
            )
        ]
        verbose_name = "семестр"
        verbose_name_plural = "семестры"

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        if not all((self.start_date, self.session_start, self.session_end, self.end_date)):
            return
        if not (self.start_date <= self.session_start <= self.session_end <= self.end_date):
            raise ValidationError(
                "Даты должны идти по порядку: начало ≤ начало сессии ≤ конец сессии ≤ окончание."
            )
        overlap = (
            Term.objects.exclude(pk=self.pk)
            .filter(start_date__lte=self.end_date, end_date__gte=self.start_date)
            .first()
        )
        if overlap is not None:
            raise ValidationError(f"Семестр пересекается с семестром «{overlap.name}».")


class CurriculumItem(models.Model):
    group = models.ForeignKey(
        "university.StudyGroup",
        on_delete=models.PROTECT,
        related_name="curriculum_items",
        verbose_name="группа",
    )
    discipline = models.ForeignKey(
        "university.Discipline",
        on_delete=models.PROTECT,
        related_name="curriculum_items",
        verbose_name="дисциплина",
    )
    term = models.ForeignKey(
        Term, on_delete=models.PROTECT, related_name="curriculum_items", verbose_name="семестр"
    )
    assessment_form = models.CharField(
        "форма контроля", max_length=16, choices=AssessmentForm.choices
    )
    credits = models.PositiveSmallIntegerField(
        "зачётные единицы",
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
    )

    class Meta:
        ordering = ["term", "discipline__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "discipline", "term"], name="academics_curriculum_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(credits__isnull=True)
                | (models.Q(credits__gte=1) & models.Q(credits__lte=30)),
                name="academics_curriculum_credits_range",
            ),
        ]
        verbose_name = "учебный план"
        verbose_name_plural = "учебные планы"

    def __str__(self) -> str:
        return f"{self.discipline} — {self.group} ({self.term})"

    @property
    def allowed_results(self) -> set[str]:
        return (
            PASS_FAIL_RESULTS if self.assessment_form == AssessmentForm.CREDIT else NUMERIC_RESULTS
        )


class CurrentMark(models.Model):
    student = models.ForeignKey(
        "accounts.StudentProfile",
        on_delete=models.CASCADE,
        related_name="current_marks",
        verbose_name="студент",
    )
    curriculum_item = models.ForeignKey(
        CurriculumItem,
        on_delete=models.PROTECT,
        related_name="current_marks",
        verbose_name="дисциплина",
    )
    value = models.PositiveSmallIntegerField(
        "оценка", validators=[MinValueValidator(2), MaxValueValidator(5)]
    )
    date = models.DateField("дата")
    kind = models.CharField("вид работы", max_length=100)
    seed_key = models.SlugField(
        "ключ демо-данных", max_length=80, blank=True, default="", editable=False
    )

    class Meta:
        ordering = ["date", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(value__gte=2) & models.Q(value__lte=5),
                name="academics_mark_value_2_5",
            ),
            models.UniqueConstraint(
                fields=["seed_key"],
                condition=~models.Q(seed_key=""),
                name="academics_mark_unique_seed_key",
            ),
        ]
        verbose_name = "текущая оценка"
        verbose_name_plural = "текущие оценки"

    def __str__(self) -> str:
        return f"{self.value} ({self.date:%d.%m.%Y})"

    def clean(self):
        super().clean()
        if self.student_id is None or self.curriculum_item_id is None:
            return
        item = self.curriculum_item
        term = item.term
        if self.student.group_id != item.group_id:
            raise ValidationError("Студент не из группы этого учебного плана.")
        if self.date is not None:
            if not term.start_date <= self.date <= term.end_date:
                raise ValidationError("Дата вне семестра.")
            if self.date > timezone.localdate():
                raise ValidationError("Дата оценки в будущем.")


class FinalResult(models.Model):
    student = models.ForeignKey(
        "accounts.StudentProfile",
        on_delete=models.CASCADE,
        related_name="final_results",
        verbose_name="студент",
    )
    curriculum_item = models.ForeignKey(
        CurriculumItem,
        on_delete=models.PROTECT,
        related_name="final_results",
        verbose_name="дисциплина",
    )
    attempt = models.PositiveSmallIntegerField(
        "попытка", default=1, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    result = models.CharField("результат", max_length=8, choices=ResultValue.choices)
    date = models.DateField("дата")
    created_at = models.DateTimeField("создано", auto_now_add=True)

    class Meta:
        ordering = ["curriculum_item", "attempt"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "curriculum_item", "attempt"],
                name="academics_result_unique_attempt",
            ),
            models.CheckConstraint(
                condition=models.Q(attempt__gte=1) & models.Q(attempt__lte=5),
                name="academics_result_attempt_1_5",
            ),
            models.CheckConstraint(
                condition=models.Q(result__in=["5", "4", "3", "2", "pass", "fail"]),
                name="academics_result_value",
            ),
        ]
        verbose_name = "итоговый результат"
        verbose_name_plural = "итоговые результаты"

    def __str__(self) -> str:
        return f"{self.get_result_display()} (попытка {self.attempt})"

    @property
    def is_numeric(self) -> bool:
        return self.result in NUMERIC_RESULTS

    @property
    def numeric_value(self) -> int | None:
        return int(self.result) if self.is_numeric else None

    @property
    def is_positive(self) -> bool:
        return self.result in POSITIVE_RESULTS

    def clean(self):
        super().clean()
        if self.student_id is None or self.curriculum_item_id is None:
            return
        item = self.curriculum_item
        term = item.term

        if self.result and self.result not in item.allowed_results:
            labels = ", ".join(ResultValue(r).label for r in sorted(item.allowed_results))
            raise ValidationError(
                f"Для формы контроля «{item.get_assessment_form_display()}» "
                f"допустимы только: {labels}."
            )

        if self.student.group_id != item.group_id:
            raise ValidationError("Студент не из группы этого учебного плана.")

        if self.date and self.date < term.start_date:
            raise ValidationError("Дата раньше начала семестра.")
        if self.date and self.date > timezone.localdate():
            raise ValidationError("Дата результата в будущем.")

        if self.student_id is None or self.curriculum_item_id is None:
            return
        others = FinalResult.objects.filter(
            student_id=self.student_id, curriculum_item_id=self.curriculum_item_id
        ).exclude(pk=self.pk)

        if self.attempt and self.attempt > 1:
            prev = others.filter(attempt=self.attempt - 1).first()
            if prev is None:
                raise ValidationError(f"Сначала внесите попытку {self.attempt - 1}.")
            if prev.is_positive:
                raise ValidationError("Предыдущая попытка уже успешна — пересдача не нужна.")
            if self.date and prev.date and self.date < prev.date:
                raise ValidationError("Пересдача не может быть раньше предыдущей попытки.")

        if self.is_positive and others.filter(attempt__gt=self.attempt).exists():
            raise ValidationError("После успешной попытки не может быть следующих попыток.")


class Attendance(models.Model):
    student = models.ForeignKey(
        "accounts.StudentProfile",
        on_delete=models.CASCADE,
        related_name="attendance_records",
        verbose_name="студент",
    )
    weekly_lesson = models.ForeignKey(
        "schedule.WeeklyLesson",
        on_delete=models.PROTECT,
        related_name="attendance_records",
        verbose_name="занятие",
    )
    original_date = models.DateField("дата занятия по расписанию")
    status = models.CharField("статус", max_length=10, choices=AttendanceStatus.choices)

    class Meta:
        ordering = ["original_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "weekly_lesson", "original_date"],
                name="academics_attendance_one_per_occurrence",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["present", "absent", "excused"]),
                name="academics_attendance_status",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "original_date"], name="academics_att_student_date_idx")
        ]
        verbose_name = "посещаемость"
        verbose_name_plural = "посещаемость"

    def __str__(self) -> str:
        return f"{self.get_status_display()} — {self.weekly_lesson} ({self.original_date:%d.%m.%Y})"

    def clean(self):
        super().clean()
        from .services import validate_occurrence_for_student

        errors = validate_occurrence_for_student(
            self.student if self.student_id else None,
            self.weekly_lesson if self.weekly_lesson_id else None,
            self.original_date,
            today=timezone.localdate(),
        )
        if errors:
            raise ValidationError(errors)
