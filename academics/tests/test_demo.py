import os
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from academics.demo import seed_academics_demo, term_bounds
from academics.models import Attendance, CurrentMark, CurriculumItem, FinalResult, Term
from academics.mutations import save_validated
from academics.services import student_overview
from accounts.demo import seed_demo_data
from accounts.models import StudentProfile
from core.testing import FrozenClockMixin
from schedule.demo import seed_schedule_demo
from schedule.tests.helpers import aware

D = date(2026, 11, 18)


class TermBoundsTests(SimpleTestCase):
    def test_autumn(self):
        self.assertEqual(term_bounds(date(2026, 11, 18))[0], "2026-autumn")

    def test_january(self):
        self.assertEqual(term_bounds(date(2027, 1, 15))[0], "2026-autumn")

    def test_spring(self):
        self.assertEqual(term_bounds(date(2027, 3, 1))[0], "2027-spring")

    def test_prev_of_autumn(self):
        autumn = term_bounds(date(2026, 11, 18))
        self.assertEqual(term_bounds(autumn[2] - timedelta(days=1))[0], "2026-spring")


class AcademicsDemoTests(FrozenClockMixin, TestCase):
    def _seed(self, day: date = D):
        with mock.patch("django.utils.timezone.now", return_value=aware(f"{day} 12:00")):
            seed_demo_data("Demo-Pass-2026-test!")
            seed_schedule_demo(day)
            return seed_academics_demo(day)

    def _student(self, username: str) -> StudentProfile:
        return StudentProfile.objects.get(user__username=username)

    def test_counts(self):
        summary = self._seed()
        self.assertEqual(Term.objects.count(), 2)
        self.assertEqual(CurriculumItem.objects.count(), 17)
        self.assertEqual(FinalResult.objects.count(), 13)
        self.assertEqual(summary.terms, 2)
        self.assertEqual(summary.curriculum_items, 17)
        self.assertEqual(summary.results, 13)

    def test_students_differ(self):
        self._seed()
        o1 = student_overview(self._student("student1"), D)
        self.assertEqual(o1.overall_average, Decimal("5.00"))
        self.assertEqual(o1.debts, [])

        o3 = student_overview(self._student("student3"), D)
        self.assertEqual(o3.overall_average, Decimal("3.50"))
        self.assertEqual([i.discipline.name for i in o3.debts], ["Основы права"])

        o2 = student_overview(self._student("student2"), D)
        self.assertEqual(o2.overall_average, Decimal("4.50"))
        self.assertEqual(o2.debts, [])

    def test_retake_present(self):
        self._seed()
        student3 = self._student("student3")
        item = CurriculumItem.objects.get(
            group=student3.group, discipline__name="История дипломатии"
        )
        results = list(
            FinalResult.objects.filter(student=student3, curriculum_item=item).order_by("attempt")
        )
        self.assertEqual([r.attempt for r in results], [1, 2])
        self.assertEqual(results[0].result, "2")
        self.assertEqual(results[1].result, "4")

    def test_attendance_only_past_and_valid(self):
        self._seed()
        with mock.patch("django.utils.timezone.now", return_value=aware("2026-11-18 12:00")):
            for a in Attendance.objects.all():
                a.full_clean()

    def test_idempotent(self):
        self._seed()
        c1 = (
            Term.objects.count(),
            CurriculumItem.objects.count(),
            CurrentMark.objects.count(),
            FinalResult.objects.count(),
            Attendance.objects.count(),
        )
        self._seed()
        c2 = (
            Term.objects.count(),
            CurriculumItem.objects.count(),
            CurrentMark.objects.count(),
            FinalResult.objects.count(),
            Attendance.objects.count(),
        )
        self.assertEqual(c1, c2)

    def test_admin_rows_survive(self):
        self._seed()
        student1 = self._student("student1")
        item = CurriculumItem.objects.filter(group=student1.group).first()
        admin_mark = save_validated(
            CurrentMark(
                student=student1,
                curriculum_item=item,
                value=5,
                date=item.term.start_date,
                kind="Админская работа",
            )
        )
        self._seed()
        self.assertTrue(
            CurrentMark.objects.filter(pk=admin_mark.pk, kind="Админская работа").exists()
        )

    def test_rerun_later_adds_only_new_rows(self):
        self._seed()
        marks_before = CurrentMark.objects.count()
        attendance_before = Attendance.objects.count()
        self._seed(D + timedelta(days=14))
        self.assertGreaterEqual(CurrentMark.objects.count(), marks_before)
        self.assertGreaterEqual(Attendance.objects.count(), attendance_before)
        self.assertEqual(FinalResult.objects.count(), 13)
        self.assertEqual(CurriculumItem.objects.count(), 17)

    def test_page_renders_weeks_after_seed(self):
        self._seed()
        student1 = self._student("student1")
        with mock.patch(
            "django.utils.timezone.now", return_value=aware(f"{D + timedelta(days=21)} 12:00")
        ):
            self.client.force_login(student1.user)
            response = self.client.get(reverse("academics:my_grades"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("не отмечено", response.content.decode())

    def test_command_output(self):
        with (
            mock.patch.dict(os.environ, {"DEMO_PASSWORD": "Demo-Pass-2026-test!"}),
            mock.patch("django.utils.timezone.now", return_value=aware("2026-11-18 12:00")),
        ):
            out = StringIO()
            call_command("seed_demo", stdout=out)
            self.assertIn("Academics ready", out.getvalue())
