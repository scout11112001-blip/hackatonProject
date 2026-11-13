"""Fictional demo data for the deanery prototype.

All names, records and codes are invented. Password comes only from the
``DEMO_PASSWORD`` environment variable and is never printed or logged.
"""

from dataclasses import dataclass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import StaffProfile, StudentProfile, User
from university.models import Faculty, Program, StudyGroup


class DemoSeedError(Exception):
    pass


@dataclass(frozen=True)
class FacultySeed:
    code: str
    name: str


@dataclass(frozen=True)
class ProgramSeed:
    faculty_code: str
    code: str
    name: str


@dataclass(frozen=True)
class GroupSeed:
    name: str
    program_faculty_code: str
    program_code: str
    course: int


@dataclass(frozen=True)
class StudentSeed:
    username: str
    last_name: str
    first_name: str
    middle_name: str
    group_name: str
    record_number: str


@dataclass(frozen=True)
class StaffSeed:
    username: str
    last_name: str
    first_name: str
    middle_name: str
    position: str
    faculty_code: str


@dataclass(frozen=True)
class SeedSummary:
    faculties: int
    programs: int
    groups: int
    students: int
    staff: int


FACULTY_SEEDS = [
    FacultySeed(code="FDD", name="Факультет цифровой дипломатии"),
    FacultySeed(code="FAE", name="Факультет прикладной экономики"),
]

PROGRAM_SEEDS = [
    ProgramSeed(faculty_code="FDD", code="41.03.05", name="Цифровая дипломатия"),
    ProgramSeed(faculty_code="FAE", code="38.03.01", name="Экономика данных"),
]

GROUP_SEEDS = [
    GroupSeed(name="ЦД-101", program_faculty_code="FDD", program_code="41.03.05", course=1),
    GroupSeed(name="ЭД-201", program_faculty_code="FAE", program_code="38.03.01", course=2),
]

STUDENT_SEEDS = [
    StudentSeed(
        username="student1",
        last_name="Соколова",
        first_name="Анна",
        middle_name="Петровна",
        group_name="ЦД-101",
        record_number="ST-2026-0001",
    ),
    StudentSeed(
        username="student2",
        last_name="Белов",
        first_name="Максим",
        middle_name="",
        group_name="ЭД-201",
        record_number="ST-2025-0002",
    ),
    StudentSeed(
        username="student3",
        last_name="Ким",
        first_name="Дарья",
        middle_name="Сергеевна",
        group_name="ЦД-101",
        record_number="ST-2026-0003",
    ),
]

STAFF_SEEDS = [
    StaffSeed(
        username="staff1",
        last_name="Миронова",
        first_name="Елена",
        middle_name="Викторовна",
        position="Специалист деканата",
        faculty_code="FDD",
    ),
    StaffSeed(
        username="staff2",
        last_name="Кузнецов",
        first_name="Игорь",
        middle_name="Андреевич",
        position="Заместитель декана",
        faculty_code="FAE",
    ),
]


def _upsert_user(username: str, role: str, password: str) -> User:
    user = User.objects.filter(username=username).first()
    if user is not None and (user.is_superuser or user.role != role):
        raise DemoSeedError(f"User '{username}' already exists with a different role.")
    if user is None:
        user = User(username=username, role=role)
    try:
        validate_password(password, user)
    except ValidationError as exc:
        raise DemoSeedError("DEMO_PASSWORD is too weak: " + " ".join(exc.messages)) from None
    user.set_password(password)
    user.is_active = True
    user.is_staff = False
    user.is_superuser = False
    user.save()
    return user


def seed_demo_data(password: str) -> SeedSummary:
    if not password:
        raise DemoSeedError("DEMO_PASSWORD is empty.")
    with transaction.atomic():
        for seed in STUDENT_SEEDS:
            taken = (
                StudentProfile.objects.filter(record_number=seed.record_number)
                .exclude(user__username=seed.username)
                .exists()
            )
            if taken:
                raise DemoSeedError(
                    f"Record number {seed.record_number} is already used by another student; "
                    f"cannot create demo user '{seed.username}'."
                )

        faculties = {}
        for seed in FACULTY_SEEDS:
            faculty, _ = Faculty.objects.update_or_create(
                code=seed.code, defaults={"name": seed.name}
            )
            faculties[seed.code] = faculty

        programs = {}
        for seed in PROGRAM_SEEDS:
            program, _ = Program.objects.update_or_create(
                faculty=faculties[seed.faculty_code],
                code=seed.code,
                defaults={"name": seed.name},
            )
            programs[(seed.faculty_code, seed.code)] = program

        groups = {}
        for seed in GROUP_SEEDS:
            group, _ = StudyGroup.objects.update_or_create(
                name=seed.name,
                defaults={
                    "program": programs[(seed.program_faculty_code, seed.program_code)],
                    "course": seed.course,
                },
            )
            groups[seed.name] = group

        for seed in STUDENT_SEEDS:
            user = _upsert_user(seed.username, User.Role.STUDENT, password)
            StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    "last_name": seed.last_name,
                    "first_name": seed.first_name,
                    "middle_name": seed.middle_name,
                    "group": groups[seed.group_name],
                    "record_number": seed.record_number,
                },
            )

        for seed in STAFF_SEEDS:
            user = _upsert_user(seed.username, User.Role.STAFF, password)
            StaffProfile.objects.update_or_create(
                user=user,
                defaults={
                    "last_name": seed.last_name,
                    "first_name": seed.first_name,
                    "middle_name": seed.middle_name,
                    "position": seed.position,
                    "faculty": faculties[seed.faculty_code],
                },
            )

    return SeedSummary(
        faculties=len(FACULTY_SEEDS),
        programs=len(PROGRAM_SEEDS),
        groups=len(GROUP_SEEDS),
        students=len(STUDENT_SEEDS),
        staff=len(STAFF_SEEDS),
    )
