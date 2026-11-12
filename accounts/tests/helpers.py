"""Plain helper functions for account tests (no extra dependencies)."""

from accounts.models import StaffProfile, StudentProfile, User
from university.models import Faculty, Program, StudyGroup


def make_faculty(code: str) -> Faculty:
    return Faculty.objects.create(code=code, name=f"Факультет {code}")


def make_group(faculty: Faculty, name: str, course: int = 1) -> StudyGroup:
    program = Program.objects.create(faculty=faculty, code=f"PR-{name}", name=f"Программа {name}")
    return StudyGroup.objects.create(program=program, name=name, course=course)


def make_student(username: str, group: StudyGroup, record_number: str) -> User:
    user = User.objects.create_user(username=username, role=User.Role.STUDENT)
    StudentProfile.objects.create(
        user=user,
        last_name=f"{username}-last",
        first_name=f"{username}-first",
        group=group,
        record_number=record_number,
    )
    return user


def make_staff(username: str, faculty: Faculty) -> User:
    user = User.objects.create_user(username=username, role=User.Role.STAFF)
    StaffProfile.objects.create(
        user=user,
        last_name=f"{username}-last",
        first_name=f"{username}-first",
        position="Специалист деканата",
        faculty=faculty,
    )
    return user
