from datetime import date
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from academics.models import (
    Attendance,
    AttendanceStatus,
    CurrentMark,
    CurriculumItem,
    FinalResult,
    Term,
)
from academics.mutations import save_validated
from accounts.tests.helpers import make_faculty, make_group, make_student
from schedule.tests.helpers import aware, make_discipline, make_lesson, make_room

from .helpers import make_attendance, make_item, make_term

TODAY = "2026-11-18 12:00"


class ModelFixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group_x = make_group(cls.faculty, "GX")
        cls.group_y = make_group(cls.faculty, "GY")
        cls.student_a = make_student("sa", cls.group_x, "REC-A")
        cls.student_b = make_student("sb", cls.group_y, "REC-B")
        cls.profile_a = cls.student_a.student_profile
        cls.profile_b = cls.student_b.student_profile
        cls.discipline = make_discipline("Дисциплина")
        cls.term = make_term(
            code="t-2026-autumn",
            start=date(2026, 9, 1),
            end=date(2027, 1, 31),
            session_start=date(2027, 1, 10),
            session_end=date(2027, 1, 31),
        )

    def _patch_now(self):
        return mock.patch("django.utils.timezone.now", return_value=aware(TODAY))


class TermModelTests(ModelFixture):
    def test_valid_term(self):
        term = make_term(
            code="t-2026-spring",
            start=date(2026, 2, 1),
            end=date(2026, 8, 31),
            session_start=date(2026, 6, 1),
            session_end=date(2026, 6, 30),
        )
        self.assertEqual(term.code, "t-2026-spring")

    def test_dates_out_of_order_rejected(self):
        cases = [
            dict(start_date=date(2027, 1, 20)),  # start_date > session_start
            dict(session_start=date(2027, 2, 1)),  # session_start > session_end
            dict(session_end=date(2027, 2, 1)),  # session_end > end_date
        ]
        for i, overrides in enumerate(cases):
            with self.subTest(i=i):
                kwargs = dict(
                    code=f"t-out-{i}",
                    name="x",
                    start_date=date(2026, 9, 1),
                    end_date=date(2027, 1, 31),
                    session_start=date(2027, 1, 10),
                    session_end=date(2027, 1, 31),
                )
                kwargs.update(overrides)
                term = Term(**kwargs)
                with self.assertRaises(ValidationError):
                    term.full_clean()

    def test_overlapping_term_rejected(self):
        other = Term(
            code="t-overlap",
            name="Пересекающийся",
            start_date=date(2026, 10, 1),
            end_date=date(2027, 3, 31),
            session_start=date(2027, 1, 10),
            session_end=date(2027, 1, 31),
        )
        with self.assertRaises(ValidationError):
            other.full_clean()

    def test_adjacent_terms_allowed(self):
        first = make_term(
            code="t-spring",
            start=date(2026, 2, 1),
            end=date(2026, 8, 31),
            session_start=date(2026, 6, 1),
            session_end=date(2026, 6, 30),
        )
        first.full_clean()

    def test_db_constraint_dates_order(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Term.objects.create(
                    code="t-bad",
                    name="x",
                    start_date=date(2027, 1, 1),
                    end_date=date(2027, 1, 31),
                    session_start=date(2026, 12, 1),
                    session_end=date(2027, 1, 31),
                )


class CurriculumItemModelTests(ModelFixture):
    def test_duplicate_rejected(self):
        make_item(self.group_x, self.discipline, self.term)
        dup = CurriculumItem(
            group=self.group_x, discipline=self.discipline, term=self.term, assessment_form="exam"
        )
        with self.assertRaises(ValidationError):
            dup.full_clean()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CurriculumItem.objects.create(
                    group=self.group_x,
                    discipline=self.discipline,
                    term=self.term,
                    assessment_form="exam",
                )

    def test_credits_range(self):
        for bad in (0, 31):
            with self.subTest(bad=bad):
                item = CurriculumItem(
                    group=self.group_x,
                    discipline=self.discipline,
                    term=self.term,
                    assessment_form="exam",
                    credits=bad,
                )
                with self.assertRaises(ValidationError):
                    item.full_clean()
        item = CurriculumItem(
            group=self.group_x,
            discipline=self.discipline,
            term=self.term,
            assessment_form="exam",
            credits=None,
        )
        item.full_clean()

    def test_allowed_results(self):
        d1 = make_discipline("Дисциплина-credit")
        d2 = make_discipline("Дисциплина-exam")
        credit = make_item(self.group_x, d1, self.term, form="credit")
        self.assertEqual(credit.allowed_results, {"pass", "fail"})
        exam = make_item(self.group_x, d2, self.term, form="exam")
        self.assertEqual(exam.allowed_results, {"5", "4", "3", "2"})


class CurrentMarkModelTests(ModelFixture):
    def test_value_range_rejected(self):
        item = make_item(self.group_x, self.discipline, self.term)
        for bad in (1, 6):
            with self.subTest(bad=bad):
                mark = CurrentMark(
                    student=self.profile_a,
                    curriculum_item=item,
                    value=bad,
                    date=date(2026, 10, 1),
                    kind="Семинар",
                )
                with self.assertRaises(ValidationError):
                    mark.full_clean()

    def test_student_of_other_group_rejected(self):
        item = make_item(self.group_x, self.discipline, self.term)
        mark = CurrentMark(
            student=self.profile_b,
            curriculum_item=item,
            value=4,
            date=date(2026, 10, 1),
            kind="Семинар",
        )
        with self.assertRaises(ValidationError):
            mark.full_clean()

    def test_date_outside_term_rejected(self):
        item = make_item(self.group_x, self.discipline, self.term)
        for d in (date(2026, 8, 31), date(2027, 2, 1)):
            with self.subTest(d=d):
                mark = CurrentMark(
                    student=self.profile_a, curriculum_item=item, value=4, date=d, kind="Семинар"
                )
                with self.assertRaises(ValidationError):
                    mark.full_clean()

    def test_future_date_rejected(self):
        item = make_item(self.group_x, self.discipline, self.term)
        with self._patch_now():
            mark = CurrentMark(
                student=self.profile_a,
                curriculum_item=item,
                value=4,
                date=date(2026, 12, 1),
                kind="Семинар",
            )
            with self.assertRaises(ValidationError):
                mark.full_clean()

    def test_boundary_dates_allowed(self):
        item = make_item(self.group_x, self.discipline, self.term)
        with self._patch_now():
            for d in (date(2026, 9, 1), date(2026, 11, 18)):
                mark = CurrentMark(
                    student=self.profile_a, curriculum_item=item, value=4, date=d, kind="Семинар"
                )
                mark.full_clean()


class FinalResultModelTests(ModelFixture):
    def _exam(self):
        return make_item(self.group_x, self.discipline, self.term, form="exam")

    def _credit(self):
        return make_item(self.group_x, self.discipline, self.term, form="credit")

    def _graded(self):
        return make_item(self.group_x, self.discipline, self.term, form="graded_credit")

    def test_numeric_on_credit_rejected(self):
        credit = self._credit()
        r = FinalResult(
            student=self.profile_a,
            curriculum_item=credit,
            attempt=1,
            result="5",
            date=date(2026, 10, 1),
        )
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_pass_on_exam_rejected(self):
        exam = self._exam()
        r = FinalResult(
            student=self.profile_a,
            curriculum_item=exam,
            attempt=1,
            result="pass",
            date=date(2026, 10, 1),
        )
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_pass_on_graded_credit_rejected(self):
        graded = self._graded()
        r = FinalResult(
            student=self.profile_a,
            curriculum_item=graded,
            attempt=1,
            result="pass",
            date=date(2026, 10, 1),
        )
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_numeric_on_graded_credit_allowed(self):
        graded = self._graded()
        r = FinalResult(
            student=self.profile_a,
            curriculum_item=graded,
            attempt=1,
            result="4",
            date=date(2026, 10, 1),
        )
        r.full_clean()

    def test_student_of_other_group_rejected(self):
        exam = self._exam()
        r = FinalResult(
            student=self.profile_b,
            curriculum_item=exam,
            attempt=1,
            result="4",
            date=date(2026, 10, 1),
        )
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_attempt_2_without_1_rejected(self):
        exam = self._exam()
        r = FinalResult(
            student=self.profile_a,
            curriculum_item=exam,
            attempt=2,
            result="4",
            date=date(2026, 10, 1),
        )
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_retake_after_positive_rejected(self):
        exam = self._exam()
        save_validated(
            FinalResult(
                student=self.profile_a,
                curriculum_item=exam,
                attempt=1,
                result="4",
                date=date(2026, 10, 1),
            )
        )
        r = FinalResult(
            student=self.profile_a,
            curriculum_item=exam,
            attempt=2,
            result="5",
            date=date(2026, 10, 10),
        )
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_retake_earlier_date_rejected(self):
        exam = self._exam()
        save_validated(
            FinalResult(
                student=self.profile_a,
                curriculum_item=exam,
                attempt=1,
                result="2",
                date=date(2026, 10, 10),
            )
        )
        r = FinalResult(
            student=self.profile_a,
            curriculum_item=exam,
            attempt=2,
            result="4",
            date=date(2026, 10, 5),
        )
        with self.assertRaises(ValidationError):
            r.full_clean()

    def test_retake_after_fail_allowed(self):
        exam = self._exam()
        save_validated(
            FinalResult(
                student=self.profile_a,
                curriculum_item=exam,
                attempt=1,
                result="2",
                date=date(2026, 10, 10),
            )
        )
        r = FinalResult(
            student=self.profile_a,
            curriculum_item=exam,
            attempt=2,
            result="4",
            date=date(2026, 10, 20),
        )
        r.full_clean()

    def test_positive_earlier_attempt_with_later_attempt_rejected(self):
        exam = self._exam()
        first = save_validated(
            FinalResult(
                student=self.profile_a,
                curriculum_item=exam,
                attempt=1,
                result="2",
                date=date(2026, 10, 1),
            )
        )
        save_validated(
            FinalResult(
                student=self.profile_a,
                curriculum_item=exam,
                attempt=2,
                result="4",
                date=date(2026, 10, 10),
            )
        )
        first.result = "5"
        with self.assertRaises(ValidationError):
            first.full_clean()

    def test_duplicate_attempt_rejected(self):
        exam = self._exam()
        save_validated(
            FinalResult(
                student=self.profile_a,
                curriculum_item=exam,
                attempt=1,
                result="2",
                date=date(2026, 10, 1),
            )
        )
        dup = FinalResult(
            student=self.profile_a,
            curriculum_item=exam,
            attempt=1,
            result="3",
            date=date(2026, 10, 2),
        )
        with self.assertRaises(ValidationError):
            dup.full_clean()

    def test_future_date_rejected(self):
        exam = self._exam()
        with self._patch_now():
            r = FinalResult(
                student=self.profile_a,
                curriculum_item=exam,
                attempt=1,
                result="4",
                date=date(2026, 12, 1),
            )
            with self.assertRaises(ValidationError):
                r.full_clean()

    def test_db_constraint_result_value(self):
        exam = self._exam()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FinalResult.objects.create(
                    student=self.profile_a,
                    curriculum_item=exam,
                    attempt=1,
                    result="7",
                    date=date(2026, 10, 1),
                )


class AttendanceModelTests(ModelFixture):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.room = make_room("room-101")
        cls.lesson = make_lesson(
            [cls.group_x],
            0,
            2,
            cls.room,
            discipline=cls.discipline,
            valid_from=date(2026, 9, 1),
            valid_until=date(2026, 12, 31),
        )

    def test_valid_record(self):
        with self._patch_now():
            make_attendance(self.profile_a, self.lesson, date(2026, 11, 16), "present")

    def test_other_group_rejected(self):
        with self._patch_now():
            a = Attendance(
                student=self.profile_b,
                weekly_lesson=self.lesson,
                original_date=date(2026, 11, 16),
                status="present",
            )
            with self.assertRaises(ValidationError):
                a.full_clean()

    def test_wrong_weekday_rejected(self):
        with self._patch_now():
            a = Attendance(
                student=self.profile_a,
                weekly_lesson=self.lesson,
                original_date=date(2026, 11, 17),
                status="present",
            )
            with self.assertRaises(ValidationError):
                a.full_clean()

    def test_outside_validity_rejected(self):
        with self._patch_now():
            a = Attendance(
                student=self.profile_a,
                weekly_lesson=self.lesson,
                original_date=date(2027, 1, 4),
                status="present",
            )
            with self.assertRaises(ValidationError):
                a.full_clean()

    def test_cancelled_rejected(self):
        from schedule.models import ChangeKind, LessonChange
        from schedule.mutations import save_lesson_change

        save_lesson_change(
            LessonChange(
                weekly_lesson=self.lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="Отмена",
            )
        )
        with self._patch_now():
            a = Attendance(
                student=self.profile_a,
                weekly_lesson=self.lesson,
                original_date=date(2026, 11, 16),
                status="present",
            )
            with self.assertRaises(ValidationError):
                a.full_clean()

    def test_future_rejected(self):
        with self._patch_now():
            a = Attendance(
                student=self.profile_a,
                weekly_lesson=self.lesson,
                original_date=date(2026, 11, 23),
                status="present",
            )
            with self.assertRaises(ValidationError):
                a.full_clean()

    def test_moved_to_future_rejected(self):
        from schedule.models import ChangeKind, LessonChange
        from schedule.mutations import save_lesson_change

        save_lesson_change(
            LessonChange(
                weekly_lesson=self.lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 20),
                new_slot=5,
                reason="Перенос",
            )
        )
        with self._patch_now():
            a = Attendance(
                student=self.profile_a,
                weekly_lesson=self.lesson,
                original_date=date(2026, 11, 16),
                status="present",
            )
            with self.assertRaises(ValidationError):
                a.full_clean()

    def test_moved_to_past_allowed(self):
        from schedule.models import ChangeKind, LessonChange
        from schedule.mutations import save_lesson_change

        lesson2 = make_lesson(
            [self.group_x],
            0,
            3,
            self.room,
            valid_from=date(2026, 9, 1),
            valid_until=date(2026, 12, 31),
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson2,
                original_date=date(2026, 11, 9),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 11),
                new_slot=5,
                reason="Перенос",
            )
        )
        with self._patch_now():
            make_attendance(self.profile_a, lesson2, date(2026, 11, 9), "present")

    def test_today_allowed(self):
        lesson3 = make_lesson(
            [self.group_x],
            2,
            2,
            self.room,
            valid_from=date(2026, 9, 1),
            valid_until=date(2026, 12, 31),
        )
        with self._patch_now():
            make_attendance(self.profile_a, lesson3, date(2026, 11, 18), "present")

    def test_duplicate_rejected(self):
        with self._patch_now():
            make_attendance(self.profile_a, self.lesson, date(2026, 11, 16), "present")
            dup = Attendance(
                student=self.profile_a,
                weekly_lesson=self.lesson,
                original_date=date(2026, 11, 16),
                status="absent",
            )
            with self.assertRaises(ValidationError):
                dup.full_clean()
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    Attendance.objects.create(
                        student=self.profile_a,
                        weekly_lesson=self.lesson,
                        original_date=date(2026, 11, 16),
                        status="absent",
                    )

    def test_db_status_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Attendance.objects.create(
                    student=self.profile_a,
                    weekly_lesson=self.lesson,
                    original_date=date(2026, 11, 16),
                    status="late",
                )

    def test_no_late_status_choice(self):
        self.assertNotIn("late", AttendanceStatus.values)
