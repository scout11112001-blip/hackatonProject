from datetime import date, time
from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from academics.models import (
    FinalResult,
    Term,
)
from academics.services import (
    average_grade,
    current_term,
    effective_results,
    is_debt,
    status_text,
    student_overview,
    student_term_report,
    summarize_attendance,
)
from accounts.tests.helpers import make_faculty, make_group, make_student
from core.testing import FrozenClockMixin
from schedule.models import WeeklyLesson
from schedule.services import ItemKind, ScheduleItem
from schedule.tests.helpers import make_discipline
from schedule.timeslots import TimeSlot

from .helpers import make_item, make_mark, make_result, make_term

TODAY = date(2026, 11, 18)


def _res(item_id: int, attempt: int, result: str) -> FinalResult:
    return FinalResult(curriculum_item_id=item_id, attempt=attempt, result=result)


def _avg_values(values) -> list[FinalResult]:
    return [FinalResult(result=str(v)) for v in values]


class EffectiveResultsTests(SimpleTestCase):
    def test_single_attempt(self):
        r = _res(1, 1, "4")
        self.assertEqual(effective_results([r]), {1: r})

    def test_retake_attempt_2_wins(self):
        r1 = _res(1, 1, "2")
        r2 = _res(1, 2, "4")
        eff = effective_results([r1, r2])
        self.assertIs(eff[1], r2)

    def test_empty(self):
        self.assertEqual(effective_results([]), {})


class AverageGradeTests(SimpleTestCase):
    def test_three_values(self):
        self.assertEqual(average_grade(_avg_values([5, 4, 4])), Decimal("4.33"))

    def test_half(self):
        self.assertEqual(average_grade(_avg_values([5, 4])), Decimal("4.50"))

    def test_round_up(self):
        self.assertEqual(average_grade(_avg_values([4, 5, 5])), Decimal("4.67"))

    def test_half_up(self):
        self.assertEqual(
            average_grade(_avg_values([4, 5, 4, 5, 4, 5, 4, 4])),
            Decimal("4.38"),
        )

    def test_only_pass_fail_none(self):
        self.assertIsNone(average_grade([FinalResult(result="pass"), FinalResult(result="fail")]))

    def test_includes_two(self):
        self.assertEqual(average_grade(_avg_values([5, 2])), Decimal("3.50"))


class IsDebtTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.discipline = make_discipline("Дисциплина")
        # finished session: session_end < today (2026-11-18)
        cls.finished = make_term(
            code="t-finished",
            start=date(2026, 2, 1),
            end=date(2026, 8, 31),
            session_start=date(2026, 6, 1),
            session_end=date(2026, 6, 30),
        )
        # unfinished session: session_end > today
        cls.open = make_term(
            code="t-open",
            start=date(2026, 9, 1),
            end=date(2027, 1, 31),
            session_start=date(2027, 1, 10),
            session_end=date(2027, 1, 31),
        )
        cls.item_finished = make_item(cls.group, cls.discipline, cls.finished)
        cls.item_open = make_item(cls.group, cls.discipline, cls.open, form="exam")

    def test_session_not_finished_missing(self):
        self.assertFalse(is_debt(self.item_open, None, TODAY))

    def test_finished_missing(self):
        self.assertTrue(is_debt(self.item_finished, None, TODAY))

    def test_finished_two(self):
        self.assertTrue(is_debt(self.item_finished, _res(1, 1, "2"), TODAY))

    def test_finished_fail(self):
        self.assertTrue(is_debt(self.item_finished, _res(1, 1, "fail"), TODAY))

    def test_finished_three(self):
        self.assertFalse(is_debt(self.item_finished, _res(1, 1, "3"), TODAY))

    def test_retake_clears(self):
        self.assertFalse(is_debt(self.item_finished, _res(1, 2, "3"), TODAY))

    def test_boundary(self):
        # today == session_end -> not finished
        self.assertFalse(is_debt(self.item_finished, None, date(2026, 6, 30)))
        self.assertTrue(is_debt(self.item_finished, None, date(2026, 7, 1)))


class StatusTextTests(SimpleTestCase):
    def test_zero(self):
        self.assertEqual(status_text(0), "Всё в порядке")

    def test_debts(self):
        self.assertEqual(status_text(3), "Есть задолженности: 3")


class SummarizeAttendanceTests(FrozenClockMixin, TestCase):
    def _item(self, lesson_id, d, original, slot_num):
        lesson = WeeklyLesson()
        lesson.id = lesson_id
        lesson.lesson_type = "lecture"
        return ScheduleItem(
            kind=ItemKind.REGULAR,
            date=d,
            slot=TimeSlot(slot_num, time(9, 0), time(10, 30)),
            lesson=lesson,
            original_date=original,
            room=None,
            teacher=None,
        )

    def test_all_present(self):
        items = [self._item(1, date(2026, 11, 16), date(2026, 11, 16), 1)]
        records = {(1, date(2026, 11, 16)): "present"}
        summary, entries = summarize_attendance(items, records, TODAY)
        self.assertEqual(summary.percent, 100)
        self.assertEqual(summary.present, 1)

    def test_3_present_1_absent(self):
        items = [
            self._item(1, date(2026, 11, 16), date(2026, 11, 16), 1),
            self._item(2, date(2026, 11, 16), date(2026, 11, 16), 2),
            self._item(3, date(2026, 11, 16), date(2026, 11, 16), 3),
            self._item(4, date(2026, 11, 16), date(2026, 11, 16), 4),
        ]
        records = {
            (1, date(2026, 11, 16)): "present",
            (2, date(2026, 11, 16)): "present",
            (3, date(2026, 11, 16)): "present",
            (4, date(2026, 11, 16)): "absent",
        }
        summary, _ = summarize_attendance(items, records, TODAY)
        self.assertEqual(summary.percent, 75)

    def test_2_present_1_absent(self):
        items = [
            self._item(1, date(2026, 11, 16), date(2026, 11, 16), 1),
            self._item(2, date(2026, 11, 16), date(2026, 11, 16), 2),
            self._item(3, date(2026, 11, 16), date(2026, 11, 16), 3),
        ]
        records = {
            (1, date(2026, 11, 16)): "present",
            (2, date(2026, 11, 16)): "present",
            (3, date(2026, 11, 16)): "absent",
        }
        summary, _ = summarize_attendance(items, records, TODAY)
        self.assertEqual(summary.percent, 67)

    def test_all_excused(self):
        items = [
            self._item(1, date(2026, 11, 16), date(2026, 11, 16), 1),
            self._item(2, date(2026, 11, 16), date(2026, 11, 16), 2),
            self._item(3, date(2026, 11, 16), date(2026, 11, 16), 3),
        ]
        records = {
            (1, date(2026, 11, 16)): "excused",
            (2, date(2026, 11, 16)): "excused",
            (3, date(2026, 11, 16)): "excused",
        }
        summary, _ = summarize_attendance(items, records, TODAY)
        self.assertIsNone(summary.percent)
        self.assertEqual(summary.marked, 3)

    def test_no_records_two_past(self):
        items = [
            self._item(1, date(2026, 11, 16), date(2026, 11, 16), 1),
            self._item(2, date(2026, 11, 17), date(2026, 11, 17), 1),
        ]
        summary, entries = summarize_attendance(items, {}, TODAY)
        self.assertEqual(summary.unmarked, 2)
        self.assertIsNone(summary.percent)
        self.assertEqual(len(entries), 2)

    def test_future_unmarked_not_counted(self):
        items = [self._item(1, date(2026, 11, 23), date(2026, 11, 23), 1)]
        summary, entries = summarize_attendance(items, {}, TODAY)
        self.assertEqual(summary.unmarked, 0)
        self.assertEqual(entries, [])

    def test_today_marked_counted_unmarked_not(self):
        items = [
            self._item(1, date(2026, 11, 18), date(2026, 11, 18), 1),
            self._item(2, date(2026, 11, 18), date(2026, 11, 18), 2),
        ]
        records = {(1, date(2026, 11, 18)): "present"}
        summary, entries = summarize_attendance(items, records, TODAY)
        self.assertEqual(summary.present, 1)
        self.assertEqual(summary.unmarked, 0)
        self.assertEqual(len(entries), 1)

    def test_record_not_in_occurrences_ignored(self):
        items = [self._item(1, date(2026, 11, 16), date(2026, 11, 16), 1)]
        records = {(99, date(2026, 11, 16)): "present"}
        summary, _ = summarize_attendance(items, records, TODAY)
        self.assertEqual(summary.present, 0)
        self.assertEqual(summary.unmarked, 1)


class CurrentTermTests(FrozenClockMixin, TestCase):
    def _make(self, code, start, end):
        return make_term(
            code=code,
            start=start,
            end=end,
            session_start=start,
            session_end=end,
        )

    def _get(self, code):
        return Term.objects.get(code=code)

    def test_inside(self):
        t = self._make("t-a", date(2026, 9, 1), date(2027, 1, 31))
        self.assertEqual(current_term(date(2026, 11, 18)), t)

    def test_between_terms_previous(self):
        t_a = self._make("t-a", date(2026, 2, 1), date(2026, 6, 30))
        self._make("t-b", date(2026, 9, 1), date(2027, 1, 31))
        self.assertEqual(current_term(date(2026, 7, 15)), t_a)

    def test_before_all_terms_earliest(self):
        t_a = self._make("t-a", date(2026, 2, 1), date(2026, 6, 30))
        self._make("t-b", date(2026, 9, 1), date(2027, 1, 31))
        self.assertEqual(current_term(date(2026, 1, 1)), t_a)

    def test_no_terms(self):
        self.assertIsNone(current_term(date(2026, 11, 18)))


class ReportFixture(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.student = make_student("s", cls.group, "REC")
        cls.profile = cls.student.student_profile
        cls.term = make_term(
            code="t-autumn",
            start=date(2026, 9, 1),
            end=date(2027, 1, 31),
            session_start=date(2027, 1, 10),
            session_end=date(2027, 1, 31),
        )
        cls.discipline = make_discipline("Дисциплина")
        cls.item = make_item(cls.group, cls.discipline, cls.term)


class StudentOverviewTests(ReportFixture):
    def test_no_results_status_ok_before_session_end(self):
        overview = student_overview(self.profile, TODAY)
        self.assertEqual(overview.status_text, "Всё в порядке")
        self.assertEqual(overview.debts, [])

    def test_missing_result_after_session_is_debt(self):
        make_term(
            code="t-spring",
            start=date(2026, 2, 1),
            end=date(2026, 8, 31),
            session_start=date(2026, 6, 1),
            session_end=date(2026, 6, 30),
        )
        spring_item = make_item(self.group, self.discipline, Term.objects.get(code="t-spring"))
        overview = student_overview(self.profile, TODAY)
        self.assertEqual(overview.status_text, "Есть задолженности: 1")
        self.assertEqual([i.id for i in overview.debts], [spring_item.id])

    def test_retake_clears_debt(self):
        spring = make_term(
            code="t-spring2",
            start=date(2026, 2, 1),
            end=date(2026, 8, 31),
            session_start=date(2026, 6, 1),
            session_end=date(2026, 6, 30),
        )
        spring_item = make_item(self.group, self.discipline, spring)
        make_result(self.profile, spring_item, "2", attempt=1, date=date(2026, 6, 5))
        make_result(self.profile, spring_item, "4", attempt=2, date=date(2026, 6, 20))
        overview = student_overview(self.profile, TODAY)
        self.assertEqual(overview.debts, [])

    def test_only_pass_fail_average_none(self):
        credit_item = make_item(
            self.group, make_discipline("Дисциплина-credit"), self.term, form="credit"
        )
        make_result(self.profile, credit_item, "pass", date=date(2026, 10, 1))
        overview = student_overview(self.profile, TODAY)
        self.assertIsNone(overview.overall_average)

    def test_overall_average_across_terms(self):
        make_result(self.profile, self.item, "5", date=date(2026, 10, 1))
        overview = student_overview(self.profile, TODAY)
        self.assertEqual(overview.overall_average, Decimal("5.00"))

    def test_debt_count_in_status_text(self):
        spring = make_term(
            code="t-spring3",
            start=date(2026, 2, 1),
            end=date(2026, 8, 31),
            session_start=date(2026, 6, 1),
            session_end=date(2026, 6, 30),
        )
        make_item(self.group, make_discipline("Дисциплина2"), spring)
        make_item(self.group, make_discipline("Дисциплина3"), spring)
        overview = student_overview(self.profile, TODAY)
        self.assertEqual(overview.status_text, "Есть задолженности: 2")


class StudentTermReportTests(ReportFixture):
    def test_report_groups_by_discipline(self):
        make_item(self.group, make_discipline("Дисциплина2"), self.term)
        report = student_term_report(self.profile, self.term, TODAY)
        self.assertEqual(len(report.disciplines), 2)

    def test_marks_and_attempts_attached(self):
        make_mark(self.profile, self.item, 4, date(2026, 10, 1))
        make_result(self.profile, self.item, "3", date=date(2026, 10, 5))
        report = student_term_report(self.profile, self.term, TODAY)
        d = report.disciplines[0]
        self.assertEqual(len(d.marks), 1)
        self.assertEqual(len(d.attempts), 1)

    def test_empty_term(self):
        empty_term = make_term(
            code="t-spring-empty",
            start=date(2026, 2, 1),
            end=date(2026, 8, 31),
            session_start=date(2026, 6, 1),
            session_end=date(2026, 6, 30),
        )
        report = student_term_report(self.profile, empty_term, TODAY)
        self.assertEqual(report.disciplines, [])
        self.assertIsNone(report.average)

    def test_term_before_start_has_no_attendance(self):
        report = student_term_report(self.profile, self.term, date(2026, 8, 1))
        d = report.disciplines[0]
        self.assertEqual(d.attendance.marked, 0)
        self.assertEqual(d.attendance_entries, [])
