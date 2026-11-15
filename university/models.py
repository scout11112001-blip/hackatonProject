from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

NBSP = "\u00a0"


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


class Room(models.Model):
    code = models.CharField(
        "код",
        max_length=32,
        unique=True,
        validators=[
            RegexValidator(
                r"^[a-z][a-z0-9-]*$",
                "Код: латинские строчные буквы, цифры и дефис; начинается с буквы.",
            )
        ],
    )
    floor = models.PositiveSmallIntegerField(
        "этаж", validators=[MinValueValidator(1), MaxValueValidator(20)]
    )
    number = models.CharField("номер", max_length=10, unique=True)

    class Meta:
        ordering = ["floor", "number"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(floor__gte=1) & models.Q(floor__lte=20),
                name="university_room_floor_1_20",
            )
        ]
        verbose_name = "аудитория"
        verbose_name_plural = "аудитории"

    def __str__(self) -> str:
        return f"ауд. {self.number}"


class Teacher(models.Model):
    last_name = models.CharField("фамилия", max_length=100)
    first_name = models.CharField("имя", max_length=100)
    middle_name = models.CharField("отчество", max_length=100, blank=True, default="")
    title = models.CharField("учёная степень, звание", max_length=100, blank=True, default="")

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["last_name", "first_name", "middle_name"],
                name="university_teacher_unique_name",
            )
        ]
        verbose_name = "преподаватель"
        verbose_name_plural = "преподаватели"

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        return " ".join(
            part for part in (self.last_name, self.first_name, self.middle_name) if part
        )

    @property
    def short_name(self) -> str:
        middle = f"{NBSP}{self.middle_name[0]}." if self.middle_name else ""
        return f"{self.last_name}{NBSP}{self.first_name[0]}.{middle}"


class Discipline(models.Model):
    name = models.CharField("название", max_length=200, unique=True)
    short_name = models.CharField("краткое название", max_length=50)

    class Meta:
        ordering = ["name"]
        verbose_name = "дисциплина"
        verbose_name_plural = "дисциплины"

    def __str__(self) -> str:
        return self.name
