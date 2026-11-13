"""Fictional academics demo data.

Creates missing rows only; never updates existing rows (admin-created data
always survives). Terms are calendar-based so the data renders weeks later.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from django.db import transaction

from academics.models import Attendance, CurrentMark, CurriculumItem, FinalResult, Term
from academics.mutations import save_validated
from accounts.models import StudentProfile
from schedule.services import occurrences_between
from university.models import Discipline, StudyGroup

NEW_DISCIPLINES = [
    ("История дипломатии", "Ист. дипл."),
    ("Математика", "Матем."),
    ("Основы права", "Право"),
    ("Английский язык", "Англ. яз."),
]

PREV_CURRICULUM = [
    ("ЦД-101", "История дипломатии", "exam", 5),
    ("ЦД-101", "Математика", "graded_credit", 4),
    ("ЦД-101", "Основы права", "credit", 2),
    ("ЦД-101", "Английский язык", "credit", 3),
    ("ЭД-201", "Математика", "exam", 5),
    ("ЭД-201", "Основы права", "credit", 2),
    ("ЭД-201", "Английский язык", "graded_credit", 3),
    ("ЭД-201", "История дипломатии", "credit", 2),
]

CUR_CURRICULUM = [
    ("ЦД-101", "Введение в цифровую дипломатию", "exam", 5),
    ("ЦД-101", "Теория международных отношений", "exam", 4),
    ("ЦД-101", "Английский язык", "graded_credit", 3),
    ("ЦД-101", "Анализ данных на Python", "credit", 3),
    ("ЦД-101", "Философия", "credit", 2),
    ("ЭД-201", "Микроэкономика", "exam", 5),
    ("ЭД-201", "Анализ данных на Python", "graded_credit", 4),
    ("ЭД-201", "Английский язык", "credit", 3),
    ("ЭД-201", "Философия", "credit", 2),
]

PREV_RESULTS = [
    ("student1", "История дипломатии", 1, "5", 2),
    ("student1", "Математика", 1, "5", 5),
    ("student1", "Основы права", 1, "pass", 8),
    ("student1", "Английский язык", 1, "pass", 11),
    ("student3", "История дипломатии", 1, "2", 2),
    ("student3", "История дипломатии", 2, "4", 20),
    ("student3", "Математика", 1, "3", 5),
    ("student3", "Основы права", 1, "fail", 8),
    ("student3", "Английский язык", 1, "pass", 11),
    ("student2", "Математика", 1, "4", 3),
    ("student2", "Основы права", 1, "pass", 6),
    ("student2", "Английский язык", 1, "5", 9),
    ("student2", "История дипломатии", 1, "pass", 12),
]

PATTERN = {
    "student1": [5, 5, 4, 5, 5],
    "student3": [3, 2, 4, 3, 3],
    "student2": [4, 5, 4, 4, 5],
}

KINDS = ["Семинар", "Контрольная работа", "Доклад", "Семинар", "Тест"]


@dataclass(frozen=True)
class AcademicsSeedSummary:
    terms: int
    curriculum_items: int
    marks: int
    results: int
    attendance: int


def term_bounds(day: date) -> tuple[str, str, date, date, date, date]:
    if day.month >= 9:
        y = day.year
        return (
            f"{y}-autumn",
            f"Осенний семестр {y}/{y + 1}",
            date(y, 9, 1),
            date(y + 1, 1, 31),
            date(y + 1, 1, 10),
            date(y + 1, 1, 31),
        )
    if day.month == 1:
        y = day.year - 1
        return (
            f"{y}-autumn",
            f"Осенний семестр {y}/{y + 1}",
            date(y, 9, 1),
            date(y + 1, 1, 31),
            date(y + 1, 1, 10),
            date(y + 1, 1, 31),
        )
    y = day.year
    return (
        f"{y}-spring",
        f"Весенний семестр {y}",
        date(y, 2, 1),
        date(y, 8, 31),
        date(y, 6, 1),
        date(y, 6, 30),
    )


def seed_academics_demo(today: date) -> AcademicsSeedSummary:
    cur_bounds = term_bounds(today)
    prev_bounds = term_bounds(cur_bounds[2] - timedelta(days=1))

    with transaction.atomic():
        terms = {}
        for bounds in (prev_bounds, cur_bounds):
            code, name, start, end, ss, se = bounds
            term = Term.objects.filter(code=code).first()
            if term is None:
                term = save_validated(
                    Term(
                        code=code,
                        name=name,
                        start_date=start,
                        end_date=end,
                        session_start=ss,
                        session_end=se,
                    )
                )
            terms[code] = term

        disciplines = {}
        for name, short in NEW_DISCIPLINES:
            discipline, _ = Discipline.objects.get_or_create(
                name=name, defaults={"short_name": short}
            )
            disciplines[name] = discipline

        all_names = {d for _, d, _, _ in PREV_CURRICULUM} | {d for _, d, _, _ in CUR_CURRICULUM}
        for name in all_names:
            if name not in disciplines:
                discipline, _ = Discipline.objects.get_or_create(
                    name=name, defaults={"short_name": name[:10]}
                )
                disciplines[name] = discipline

        groups = {g.name: g for g in StudyGroup.objects.filter(name__in=("ЦД-101", "ЭД-201"))}
        students = {
            s.user.username: s
            for s in StudentProfile.objects.filter(
                user__username__in=("student1", "student2", "student3")
            )
        }

        curriculum: dict[tuple[str, str, str], CurriculumItem] = {}
        for table, term_code in (
            (PREV_CURRICULUM, prev_bounds[0]),
            (CUR_CURRICULUM, cur_bounds[0]),
        ):
            for group_name, discipline_name, form, credits in table:
                item = CurriculumItem.objects.filter(
                    group=groups[group_name],
                    discipline=disciplines[discipline_name],
                    term=terms[term_code],
                ).first()
                if item is None:
                    item = save_validated(
                        CurriculumItem(
                            group=groups[group_name],
                            discipline=disciplines[discipline_name],
                            term=terms[term_code],
                            assessment_form=form,
                            credits=credits,
                        )
                    )
                curriculum[(group_name, discipline_name, term_code)] = item

        prev_code = prev_bounds[0]
        for username, discipline_name, attempt, result, offset in PREV_RESULTS:
            item = curriculum[(students[username].group.name, discipline_name, prev_code)]
            existing = FinalResult.objects.filter(
                student=students[username], curriculum_item=item, attempt=attempt
            ).first()
            if existing is None:
                d = prev_bounds[4] + timedelta(days=offset)
                if d > prev_bounds[3]:
                    d = prev_bounds[3]
                save_validated(
                    FinalResult(
                        student=students[username],
                        curriculum_item=item,
                        attempt=attempt,
                        result=result,
                        date=d,
                    )
                )

        cur_code = cur_bounds[0]
        cur_start = cur_bounds[2]
        for username, profile in students.items():
            group_items = [
                (gname, discipline_name)
                for gname, discipline_name, _form, _credits in CUR_CURRICULUM
                if gname == profile.group.name
            ]
            for d, (gname, discipline_name) in enumerate(group_items):
                item = curriculum[(gname, discipline_name, cur_code)]
                for k in range(5):
                    mark_date = cur_start + timedelta(days=10 + 14 * k + d)
                    if mark_date >= today:
                        continue
                    seed_key = f"m-{cur_code}-{username}-{d}-{k}"
                    if not CurrentMark.objects.filter(seed_key=seed_key).exists():
                        save_validated(
                            CurrentMark(
                                student=profile,
                                curriculum_item=item,
                                value=PATTERN[username][(k + d) % 5],
                                date=mark_date,
                                kind=KINDS[k],
                                seed_key=seed_key,
                            )
                        )

        # Attendance: past occurrences only.
        if today - timedelta(days=1) >= cur_start:
            for username, profile in students.items():
                occ = [
                    i
                    for i in occurrences_between(
                        cur_start, today - timedelta(days=1), [profile.group_id]
                    )
                    if i.is_happening
                ]
                for item in occ:
                    n = item.original_date.toordinal() + item.slot.number
                    if username == "student1":
                        status = "excused" if n % 11 == 0 else "present"
                    elif username == "student3":
                        status = (
                            "absent" if n % 3 == 0 else ("excused" if n % 7 == 0 else "present")
                        )
                    else:
                        status = "absent" if n % 8 == 0 else "present"
                    if not Attendance.objects.filter(
                        student=profile,
                        weekly_lesson=item.lesson,
                        original_date=item.original_date,
                    ).exists():
                        save_validated(
                            Attendance(
                                student=profile,
                                weekly_lesson=item.lesson,
                                original_date=item.original_date,
                                status=status,
                            )
                        )

    marks_count = CurrentMark.objects.filter(seed_key__startswith=f"m-{cur_code}-").count()
    demo_student_ids = [s.id for s in students.values()]
    attendance_count = Attendance.objects.filter(
        student_id__in=demo_student_ids, original_date__range=(cur_start, cur_bounds[3])
    ).count()

    return AcademicsSeedSummary(
        terms=2,
        curriculum_items=len(PREV_CURRICULUM) + len(CUR_CURRICULUM),
        marks=marks_count,
        results=len(PREV_RESULTS),
        attendance=attendance_count,
    )
