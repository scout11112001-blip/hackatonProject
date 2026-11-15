from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from university.models import NBSP


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Студент"
        STAFF = "staff", "Сотрудник деканата"

    role = models.CharField("роль", max_length=16, choices=Role.choices, blank=True, default="")

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(is_superuser=False) & models.Q(role__in=["student", "staff"]))
                | (models.Q(is_superuser=True) & models.Q(role="")),
                name="accounts_user_role_matches_superuser",
                violation_error_message=(
                    "Обычный пользователь должен иметь роль; у суперпользователя роли нет."
                ),
            ),
            models.CheckConstraint(
                condition=models.Q(is_staff=False) | models.Q(is_superuser=True),
                name="accounts_user_admin_access_superuser_only",
                violation_error_message="Доступ к админке есть только у суперпользователя.",
            ),
        ]

    @property
    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT

    @property
    def is_deanery_staff(self) -> bool:
        return self.role == self.Role.STAFF

    def __str__(self) -> str:
        return self.username

    def clean(self):
        super().clean()
        if self.pk is None:
            return
        errors = []
        if (
            self.role != self.Role.STUDENT
            and StudentProfile.objects.filter(user_id=self.pk).exists()
        ):
            errors.append(
                "У пользователя есть профиль студента. Удалите профиль, затем меняйте роль."
            )
        if self.role != self.Role.STAFF and StaffProfile.objects.filter(user_id=self.pk).exists():
            errors.append(
                "У пользователя есть профиль сотрудника. Удалите профиль, затем меняйте роль."
            )
        if errors:
            raise ValidationError(errors)


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
        limit_choices_to={"role": "student"},
        verbose_name="пользователь",
    )
    last_name = models.CharField("фамилия", max_length=100)
    first_name = models.CharField("имя", max_length=100)
    middle_name = models.CharField("отчество", max_length=100, blank=True, default="")
    group = models.ForeignKey(
        "university.StudyGroup",
        on_delete=models.PROTECT,
        related_name="students",
        verbose_name="группа",
    )
    record_number = models.CharField("номер зачётной книжки", max_length=20, unique=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "профиль студента"
        verbose_name_plural = "профили студентов"

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        return " ".join(
            part for part in (self.last_name, self.first_name, self.middle_name) if part
        )

    @property
    def program(self):
        return self.group.program

    @property
    def faculty(self):
        return self.group.program.faculty

    @property
    def course(self) -> int:
        return self.group.course

    def clean(self):
        super().clean()
        if self.user_id is None:
            return
        if self.user.role != User.Role.STUDENT:
            raise ValidationError(
                "Профиль студента можно привязать только к пользователю с ролью «Студент»."
            )
        if StaffProfile.objects.filter(user_id=self.user_id).exists():
            raise ValidationError("У пользователя уже есть профиль сотрудника.")


class StaffProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_profile",
        limit_choices_to={"role": "staff"},
        verbose_name="пользователь",
    )
    last_name = models.CharField("фамилия", max_length=100)
    first_name = models.CharField("имя", max_length=100)
    middle_name = models.CharField("отчество", max_length=100, blank=True, default="")
    position = models.CharField("должность", max_length=150)
    faculty = models.ForeignKey(
        "university.Faculty",
        on_delete=models.PROTECT,
        related_name="staff_members",
        verbose_name="факультет",
    )

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "профиль сотрудника"
        verbose_name_plural = "профили сотрудников"

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

    def clean(self):
        super().clean()
        if self.user_id is None:
            return
        if self.user.role != User.Role.STAFF:
            raise ValidationError(
                "Профиль сотрудника можно привязать только к пользователю "
                "с ролью «Сотрудник деканата»."
            )
        if StudentProfile.objects.filter(user_id=self.user_id).exists():
            raise ValidationError("У пользователя уже есть профиль студента.")


class LoginThrottle(models.Model):
    username_key = models.CharField("логин", max_length=150)
    ip_address = models.GenericIPAddressField("IP-адрес")
    failures = models.PositiveIntegerField("неудачных попыток", default=0)
    first_failure_at = models.DateTimeField("первая неудача")
    last_failure_at = models.DateTimeField("последняя неудача")
    locked_until = models.DateTimeField("заблокирован до", null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["username_key", "ip_address"], name="accounts_loginthrottle_unique_key"
            )
        ]
        indexes = [models.Index(fields=["last_failure_at"], name="accounts_throttle_last_idx")]
        verbose_name = "блокировка входа"
        verbose_name_plural = "блокировки входа"

    def __str__(self) -> str:
        return f"{self.username_key} @ {self.ip_address}"
