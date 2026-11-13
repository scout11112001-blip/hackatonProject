"""Pure services for grades, results and attendance."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q

from accounts.models import StudentProfile
from schedule.models import ChangeKind, LessonChange, WeeklyLesson
from schedule.services import ScheduleItem, occurrences_between

from .models import (
    Attendance,
    AttendanceStatus,
    CurrentMark,
    CurriculumItem,
    FinalResult,
    Term,
)


@dataclass(frozen=True)
class AttendanceSummary:
    present: int
    absent: int
    excused: int
    unmarked: int

    @property
    def marked(self) -> int:
        return self.present + self.absent + self.excused

    @property
    def percent(self) -> int | None:
        if self.present + self.absent == 0:
            return None
        value = Decimal(self.present) * 100 / Decimal(self.present + self.absent)
        return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class AttendanceEntry:
    date: date
    original_date: date
    lesson_type: str
    status: str | None
    status_label: str


@dataclass(frozen=True)
class DisciplineReport:
    item: CurriculumItem
    marks: list[CurrentMark]
    attempts: list[FinalResult]
    effective: FinalResult | None
    is_debt: bool
    attendance: AttendanceSummary
    attendance_entries: list[AttendanceEntry]


@dataclass(frozen=True)
class TermReport:
    term: Term
    session_finished: bool
    disciplines: list[DisciplineReport]
    average: Decimal | None


@dataclass(frozen=True)
class StudentOverview:
    debts: list[CurriculumItem]
    status_text: str
    overall_average: Decimal | None


def validate_occurrence_for_student(
    student: StudentProfile | None,
    lesson: WeeklyLesson | None,
    original_date: date | None,
    today: date,
) -> list[str]:
    if student is None or lesson is None or original_date is None:
        return []
    errors: list[str] = []
    group_ids = set(lesson.groups.values_list("id", flat=True))
    if student.group_id not in group_ids:
        errors.append("Студент не относится к группам этого занятия.")
    if original_date.weekday() != lesson.weekday or not (
        lesson.valid_from <= original_date <= lesson.valid_until
    ):
        errors.append("В эту дату этого занятия нет по расписанию.")
        return errors
    change = LessonChange.objects.filter(weekly_lesson=lesson, original_date=original_date).first()
    if change is not None and change.kind == ChangeKind.CANCELLED:
        errors.append("Занятие отменено.")
    effective = (
        change.new_date
        if (change is not None and change.kind == ChangeKind.MOVED)
        else original_date
    )
    if effective > today:
        errors.append("Нельзя отметить посещение будущего занятия.")
    return errors


def effective_results(results: Iterable[FinalResult]) -> dict[int, FinalResult]:
    eff: dict[int, FinalResult] = {}
    for r in results:
        current = eff.get(r.curriculum_item_id)
        if current is None or r.attempt > current.attempt:
            eff[r.curriculum_item_id] = r
    return eff


def average_grade(results: Iterable[FinalResult]) -> Decimal | None:
    values = [r.numeric_value for r in results if r.is_numeric]
    if not values:
        return None
    total = Decimal(sum(values)) / Decimal(len(values))
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def is_debt(item: CurriculumItem, effective: FinalResult | None, today: date) -> bool:
    return today > item.term.session_end and (effective is None or not effective.is_positive)


def status_text(debt_count: int) -> str:
    if debt_count == 0:
        return "Всё в порядке"
    return f"Есть задолженности: {debt_count}"


def summarize_attendance(
    occurrences: Iterable[ScheduleItem],
    records: Mapping[tuple[int, date], str],
    today: date,
) -> tuple[AttendanceSummary, list[AttendanceEntry]]:
    present = absent = excused = unmarked = 0
    entries: list[AttendanceEntry] = []
    for item in sorted(occurrences, key=lambda i: (i.date, i.slot.number)):
        key = (item.lesson.id, item.original_date)
        status = records.get(key)
        if status is not None:
            if status == AttendanceStatus.PRESENT:
                present += 1
            elif status == AttendanceStatus.ABSENT:
                absent += 1
            else:
                excused += 1
            entries.append(
                AttendanceEntry(
                    date=item.date,
                    original_date=item.original_date,
                    lesson_type=item.lesson.get_lesson_type_display(),
                    status=status,
                    status_label=AttendanceStatus(status).label,
                )
            )
        elif item.date < today:
            unmarked += 1
            entries.append(
                AttendanceEntry(
                    date=item.date,
                    original_date=item.original_date,
                    lesson_type=item.lesson.get_lesson_type_display(),
                    status=None,
                    status_label="не отмечено",
                )
            )
        # today/future unmarked: skip
    summary = AttendanceSummary(present=present, absent=absent, excused=excused, unmarked=unmarked)
    return summary, entries


def current_term(today: date) -> Term | None:
    terms = list(Term.objects.all())
    for t in terms:
        if t.start_date <= today <= t.end_date:
            return t
    past = [t for t in terms if t.end_date < today]
    if past:
        return max(past, key=lambda t: t.end_date)
    future = [t for t in terms if t.start_date > today]
    if future:
        return min(future, key=lambda t: t.start_date)
    return None


def student_terms(student: StudentProfile) -> list[Term]:
    return list(
        Term.objects.filter(
            Q(curriculum_items__group_id=student.group_id)
            | Q(curriculum_items__final_results__student=student)
            | Q(curriculum_items__current_marks__student=student)
        )
        .distinct()
        .order_by("-start_date")
    )


def student_term_report(student: StudentProfile, term: Term, today: date) -> TermReport:
    items = list(
        CurriculumItem.objects.filter(term=term)
        .filter(
            Q(group_id=student.group_id)
            | Q(final_results__student=student)
            | Q(current_marks__student=student)
        )
        .distinct()
        .select_related("discipline", "term", "group")
    )

    marks = list(
        CurrentMark.objects.filter(student=student, curriculum_item__term=term).order_by(
            "date", "pk"
        )
    )
    marks_by_item: dict[int, list[CurrentMark]] = {}
    for m in marks:
        marks_by_item.setdefault(m.curriculum_item_id, []).append(m)

    results = list(
        FinalResult.objects.filter(student=student, curriculum_item__term=term).order_by("attempt")
    )
    results_by_item: dict[int, list[FinalResult]] = {}
    for r in results:
        results_by_item.setdefault(r.curriculum_item_id, []).append(r)
    eff = effective_results(results)

    if today < term.start_date:
        occ: list[ScheduleItem] = []
    else:
        end = min(term.end_date, today)
        occ = [
            i
            for i in occurrences_between(term.start_date, end, [student.group_id])
            if i.is_happening
        ]
    records = {
        (a.weekly_lesson_id, a.original_date): a.status
        for a in Attendance.objects.filter(
            student=student, weekly_lesson_id__in={i.lesson.id for i in occ}
        )
    }

    disciplines: list[DisciplineReport] = []
    for item in items:
        discipline_occ = [i for i in occ if i.lesson.discipline_id == item.discipline_id]
        summary, entries = summarize_attendance(discipline_occ, records, today)
        disciplines.append(
            DisciplineReport(
                item=item,
                marks=marks_by_item.get(item.id, []),
                attempts=results_by_item.get(item.id, []),
                effective=eff.get(item.id),
                is_debt=is_debt(item, eff.get(item.id), today),
                attendance=summary,
                attendance_entries=entries,
            )
        )
    disciplines.sort(key=lambda d: d.item.discipline.name)

    return TermReport(
        term=term,
        session_finished=today > term.session_end,
        disciplines=disciplines,
        average=average_grade(eff.values()),
    )


def student_overview(student: StudentProfile, today: date) -> StudentOverview:
    items = list(
        CurriculumItem.objects.filter(
            Q(group_id=student.group_id) | Q(final_results__student=student)
        )
        .distinct()
        .select_related("term", "discipline")
    )
    eff = effective_results(FinalResult.objects.filter(student=student))
    debts = [i for i in items if is_debt(i, eff.get(i.id), today)]
    debts.sort(key=lambda i: (i.term.start_date, i.discipline.name))
    return StudentOverview(
        debts=debts,
        status_text=status_text(len(debts)),
        overall_average=average_grade(eff.values()),
    )
