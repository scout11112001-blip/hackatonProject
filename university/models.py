from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Faculty(models.Model):
    code = models.CharField("код", max_length=20, unique=True)
    name = models.CharField("название", max_length=200, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "факультет"
        verbose_name_plural = "факультеты"

    def __str__(self) -> str:
        return self.name


class Program(models.Model):
    faculty = models.ForeignKey(
        Faculty, on_delete=models.PROTECT, related_name="programs", verbose_name="факультет"
    )
    code = models.CharField("код", max_length=20)
    name = models.CharField("название", max_length=200)

    class Meta:
        ordering = ["faculty__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["faculty", "code"], name="university_program_unique_faculty_code"
            )
        ]
        verbose_name = "направление подготовки"
        verbose_name_plural = "направления подготовки"

    def __str__(self) -> str:
        return f"{self.code} {self.name}"


class StudyGroup(models.Model):
    program = models.ForeignKey(
        Program, on_delete=models.PROTECT, related_name="groups", verbose_name="направление"
    )
    name = models.CharField("название", max_length=20, unique=True)
    course = models.PositiveSmallIntegerField(
        "курс", validators=[MinValueValidator(1), MaxValueValidator(6)]
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(course__gte=1) & models.Q(course__lte=6),
                name="university_studygroup_course_1_6",
            )
        ]
        verbose_name = "учебная группа"
        verbose_name_plural = "учебные группы"

    def __str__(self) -> str:
        return self.name

    @property
    def faculty(self) -> Faculty:
        return self.program.faculty
