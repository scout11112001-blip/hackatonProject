"""Plain helper functions for academics tests (reuse accounts/schedule helpers)."""

from datetime import date

from academics.models import Attendance, CurrentMark, CurriculumItem, FinalResult, Term
from academics.mutations import save_validated
from university.models import Discipline, StudyGroup


def make_term(
    code: str = "t-2026-autumn",
    start: date = date(2026, 9, 1),
    end: date = date(2027, 1, 31),
    session_start: date = date(2027, 1, 10),
    session_end: date = date(2027, 1, 31),
) -> Term:
    return save_validated(
        Term(
            code=code,
            name=code,
            start_date=start,
            end_date=end,
            session_start=session_start,
            session_end=session_end,
        )
    )


def make_item(
    group: StudyGroup, discipline: Discipline, term: Term, form: str = "exam", credits=None
) -> CurriculumItem:
    return save_validated(
        CurriculumItem(
            group=group,
            discipline=discipline,
            term=term,
            assessment_form=form,
            credits=credits,
        )
    )


def make_result(
    student_profile, item: CurriculumItem, result: str, attempt: int = 1, date: date | None = None
) -> FinalResult:
    if date is None:
        date = item.term.start_date
    return save_validated(
        FinalResult(
            student=student_profile,
            curriculum_item=item,
            attempt=attempt,
            result=result,
            date=date,
        )
    )


def make_mark(
    student_profile, item: CurriculumItem, value: int, date: date, kind: str = "Семинар"
) -> CurrentMark:
    return save_validated(
        CurrentMark(
            student=student_profile,
            curriculum_item=item,
            value=value,
            date=date,
            kind=kind,
        )
    )


def make_attendance(student_profile, lesson, original_date: date, status: str) -> Attendance:
    return save_validated(
        Attendance(
            student=student_profile,
            weekly_lesson=lesson,
            original_date=original_date,
            status=status,
        )
    )
