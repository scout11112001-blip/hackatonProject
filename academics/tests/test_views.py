import re
from datetime import date
from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from academics.models import Attendance, CurrentMark, CurriculumItem, FinalResult, Term
from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from core.testing import FrozenClockMixin
from schedule.models import ChangeKind, LessonChange
from schedule.mutations import save_lesson_change
from schedule.tests.helpers import aware, make_discipline, make_lesson, make_room

from .helpers import make_attendance, make_item, make_mark, make_result, make_term

NOW = "2026-11-18 12:00"


class AccessFixture(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty_x = make_faculty("FX")
        cls.faculty_y = make_faculty("FY")
        cls.group_x = make_group(cls.faculty_x, "GX")
        cls.group_y = make_group(cls.faculty_y, "GY")
        cls.student_a = make_student("a", cls.group_x, "REC-A")
        cls.student_a2 = make_student("a2", cls.group_x, "REC-A2")
        cls.student_b = make_student("b", cls.group_y, "REC-B")
        cls.staff_x = make_staff("sx", cls.faculty_x)
        cls.staff_y = make_staff("sy", cls.faculty_y)
        cls.superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")
        cls.profile_a = cls.student_a.student_profile
        cls.profile_a2 = cls.student_a2.student_profile
        cls.profile_b = cls.student_b.student_profile
        cls.term = make_term(code="t-2026-autumn")
        cls.term_prev = make_term(
            code="t-2026-spring",
            start=date(2026, 2, 1),
            end=date(2026, 8, 31),
            session_start=date(2026, 6, 1),
            session_end=date(2026, 6, 30),
        )
        cls.disc_a = make_discipline("Дисциплина-A")
        cls.disc_a2 = make_discipline("Дисциплина-A2")
        cls.disc_b = make_discipline("Дисциплина-B")
        cls.item_a = make_item(cls.group_x, cls.disc_a, cls.term)
        cls.item_a2 = make_item(cls.group_x, cls.disc_a2, cls.term)
        cls.item_b = make_item(cls.group_y, cls.disc_b, cls.term)
        cls.item_a_prev = make_item(cls.group_x, cls.disc_a, cls.term_prev)
        make_mark(cls.profile_a, cls.item_a, 5, date(2026, 10, 1), "Работа-A")
        make_mark(cls.profile_a2, cls.item_a2, 4, date(2026, 10, 1), "Работа-A2")
        make_mark(cls.profile_b, cls.item_b, 3, date(2026, 10, 1), "Работа-B")
        make_result(cls.profile_a, cls.item_a, "5", date=date(2026, 10, 5))
        make_result(cls.profile_a, cls.item_a_prev, "4", date=date(2026, 6, 10))
        make_result(cls.profile_a2, cls.item_a2, "4", date=date(2026, 10, 5))
        make_result(cls.profile_b, cls.item_b, "3", date=date(2026, 10, 5))

    def _get(self, url, user=None):
        with mock.patch("django.utils.timezone.now", return_value=aware(NOW)):
            if user is not None:
                self.client.force_login(user)
            return self.client.get(url)


class GradesAccessTests(AccessFixture):
    def test_anon_my_grades(self):
        self.assertEqual(self._get("/grades/").status_code, 302)

    def test_anon_my_grades_term(self):
        self.assertEqual(self._get(f"/grades/{self.term.code}/").status_code, 302)

    def test_anon_unknown_term(self):
        self.assertEqual(self._get("/grades/unknown-term/").status_code, 302)

    def test_anon_staff_report(self):
        self.assertEqual(self._get(f"/staff/students/{self.profile_a.pk}/grades/").status_code, 302)

    def test_anon_staff_report_term(self):
        self.assertEqual(
            self._get(f"/staff/students/{self.profile_a.pk}/grades/{self.term.code}/").status_code,
            302,
        )

    def test_student_my_grades_own(self):
        response = self._get("/grades/", self.student_a)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Работа-A", content)
        self.assertNotIn("Работа-A2", content)
        self.assertNotIn("Работа-B", content)

    def test_student_term_own(self):
        response = self._get(f"/grades/{self.term.code}/", self.student_a)
        self.assertEqual(response.status_code, 200)

    def test_student_unknown_term_404(self):
        self.assertEqual(self._get("/grades/unknown-term/", self.student_a).status_code, 404)

    def test_staff_my_grades_forbidden(self):
        self.assertEqual(self._get("/grades/", self.staff_x).status_code, 403)
        self.assertEqual(self._get("/grades/", self.staff_y).status_code, 403)

    def test_staff_my_grades_term_forbidden(self):
        self.assertEqual(self._get(f"/grades/{self.term.code}/", self.staff_x).status_code, 403)

    def test_staff_unknown_term_403(self):
        self.assertEqual(self._get("/grades/unknown-term/", self.staff_x).status_code, 403)

    def test_superuser_my_grades_forbidden(self):
        self.assertEqual(self._get("/grades/", self.superuser).status_code, 403)

    def test_superuser_my_grades_term_forbidden(self):
        self.assertEqual(self._get(f"/grades/{self.term.code}/", self.superuser).status_code, 403)

    def test_student_staff_report_forbidden(self):
        self.assertEqual(
            self._get(f"/staff/students/{self.profile_a.pk}/grades/", self.student_a).status_code,
            403,
        )

    def test_student_staff_report_term_forbidden(self):
        self.assertEqual(
            self._get(
                f"/staff/students/{self.profile_a.pk}/grades/{self.term.code}/", self.student_a
            ).status_code,
            403,
        )

    def test_staff_own_faculty_report(self):
        response = self._get(f"/staff/students/{self.profile_a.pk}/grades/", self.staff_x)
        self.assertEqual(response.status_code, 200)

    def test_staff_own_faculty_report_term(self):
        response = self._get(
            f"/staff/students/{self.profile_a.pk}/grades/{self.term.code}/", self.staff_x
        )
        self.assertEqual(response.status_code, 200)

    def test_staff_other_faculty_404(self):
        self.assertEqual(
            self._get(f"/staff/students/{self.profile_a.pk}/grades/", self.staff_y).status_code, 404
        )

    def test_staff_other_faculty_term_404(self):
        self.assertEqual(
            self._get(
                f"/staff/students/{self.profile_a.pk}/grades/{self.term.code}/", self.staff_y
            ).status_code,
            404,
        )

    def test_staff_nonexistent_student_404(self):
        self.assertEqual(self._get("/staff/students/999999/grades/", self.staff_x).status_code, 404)

    def test_superuser_staff_report_forbidden(self):
        self.assertEqual(
            self._get(f"/staff/students/{self.profile_a.pk}/grades/", self.superuser).status_code,
            403,
        )

    def test_superuser_staff_report_term_forbidden(self):
        self.assertEqual(
            self._get(
                f"/staff/students/{self.profile_a.pk}/grades/{self.term.code}/", self.superuser
            ).status_code,
            403,
        )

    def test_term_switch_keeps_isolation(self):
        self._get("/grades/", self.student_a)
        content = self._get(f"/grades/{self.term_prev.code}/", self.student_a).content.decode()
        self.assertNotIn("Работа-A2", content)
        self.assertNotIn("Работа-B", content)


class StudentGradesViewTests(AccessFixture):
    def test_default_term_is_current(self):
        response = self._get("/grades/", self.student_a)
        self.assertEqual(response.context["term"], self.term)

    def test_term_links_and_selected(self):
        response = self._get("/grades/", self.student_a)
        content = response.content.decode()
        self.assertIn(self.term.name, content)
        self.assertIn(self.term_prev.name, content)

    def test_empty_state_term_without_data(self):
        response = self._get(f"/grades/{self.term_prev.code}/", self.student_b)
        self.assertIn("За этот семестр данных нет.", response.content.decode())

    def test_no_terms_empty_state(self):
        Attendance.objects.all().delete()
        FinalResult.objects.all().delete()
        CurrentMark.objects.all().delete()
        CurriculumItem.objects.all().delete()
        Term.objects.all().delete()
        response = self._get("/grades/", self.student_a)
        self.assertIn("Семестров пока нет.", response.content.decode())

    def test_debt_marked(self):
        prev_item = make_item(self.group_x, make_discipline("Дисциплина-Debt"), self.term_prev)
        make_result(self.profile_a, prev_item, "2", date=date(2026, 6, 10))
        response = self._get("/grades/", self.student_a)
        self.assertIn("Есть задолженности: 1", response.content.decode())
        response_term = self._get(f"/grades/{self.term_prev.code}/", self.student_a)
        self.assertIn("Задолженность", response_term.content.decode())

    def test_summary_separator_glued(self):
        content = self._get("/grades/", self.student_a).content.decode()
        summaries = re.findall(r"<summary>(.*?)</summary>", content, re.S)
        self.assertTrue(summaries)
        for summary in summaries:
            self.assertIn("&nbsp;· Итог:", summary)
            self.assertIsNone(re.search(r"[ \t\n]·", summary))

    def test_ok_status(self):
        response = self._get("/grades/", self.student_a)
        self.assertIn("Всё в порядке", response.content.decode())

    def test_retake_history_shown(self):
        prev_item = make_item(self.group_x, make_discipline("Дисциплина-Retake"), self.term_prev)
        make_result(self.profile_a, prev_item, "2", attempt=1, date=date(2026, 6, 10))
        make_result(self.profile_a, prev_item, "4", attempt=2, date=date(2026, 6, 20))
        response = self._get(f"/grades/{self.term_prev.code}/", self.student_a)
        content = response.content.decode()
        self.assertIn("Попытка 1", content)
        self.assertIn("Попытка 2", content)
        self.assertIn("(действующий)", content)

    def test_attendance_summary_and_unmarked(self):
        lesson = make_lesson(
            [self.group_x],
            0,
            2,
            make_room("room-101"),
            discipline=self.disc_a,
            valid_from=date(2026, 9, 1),
            valid_until=date(2026, 12, 31),
        )
        with mock.patch("django.utils.timezone.now", return_value=aware(NOW)):
            make_attendance(self.profile_a, lesson, date(2026, 11, 16), "present")
        response = self._get("/grades/", self.student_a)
        self.assertIn("Присутствовал:", response.content.decode())

    def test_details_elements_present(self):
        response = self._get("/grades/", self.student_a)
        content = response.content.decode()
        self.assertEqual(content.count("<details>"), 2)  # item_a + item_a2

    def test_renders_weeks_later(self):
        with mock.patch("django.utils.timezone.now", return_value=aware("2026-12-09 12:00")):
            self.client.force_login(self.student_a)
            response = self.client.get("/grades/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("не отмечено", response.content.decode())

    def test_urls_have_no_ids(self):
        self.assertEqual(reverse("academics:my_grades"), "/grades/")
        self.assertEqual(
            reverse("academics:my_grades_term", kwargs={"term_code": "t"}), "/grades/t/"
        )


class StaffGradesViewTests(AccessFixture):
    def test_link_from_student_detail(self):
        response = self._get(
            reverse("accounts:staff_student_detail", args=[self.profile_a.pk]), self.staff_x
        )
        self.assertIn("Успеваемость и посещаемость", response.content.decode())

    def test_report_shows_student_name_and_back_link(self):
        response = self._get(
            reverse("academics:staff_student_grades", args=[self.profile_a.pk]), self.staff_x
        )
        content = response.content.decode()
        self.assertIn(self.profile_a.full_name, content)
        self.assertIn("К карточке студента", content)

    def test_report_matches_student_data(self):
        response = self._get(
            reverse("academics:staff_student_grades", args=[self.profile_a.pk]), self.staff_x
        )
        self.assertIn("Работа-A", response.content.decode())


class NavigationTests(AccessFixture):
    def test_student_nav_has_grades(self):
        response = self._get(reverse("accounts:profile"), self.student_a)
        self.assertIn("/grades/", response.content.decode())

    def test_staff_nav_has_no_grades(self):
        response = self._get(reverse("accounts:profile"), self.staff_x)
        self.assertNotIn("/grades/", response.content.decode())


class AdminFormTests(AccessFixture):
    def _post(self, url_name, args, data):
        self.client.force_login(self.superuser)
        return self.client.post(reverse(url_name, args=args), data)

    def test_admin_numeric_on_credit_shows_error(self):
        credit_item = make_item(
            self.group_x, make_discipline("Дисциплина-Credit"), self.term, form="credit"
        )
        response = self._post(
            "admin:academics_finalresult_add",
            [],
            {
                "student": self.profile_a.pk,
                "curriculum_item": credit_item.pk,
                "attempt": 1,
                "result": "5",
                "date": "2026-10-01",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            FinalResult.objects.filter(student=self.profile_a, curriculum_item=credit_item).exists()
        )

    def test_admin_attendance_cancelled_shows_error(self):
        lesson = make_lesson(
            [self.group_x],
            0,
            2,
            make_room("room-202"),
            valid_from=date(2026, 9, 1),
            valid_until=date(2026, 12, 31),
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="Отмена",
            )
        )
        response = self._post(
            "admin:academics_attendance_add",
            [],
            {
                "student": self.profile_a.pk,
                "weekly_lesson": lesson.pk,
                "original_date": "2026-11-16",
                "status": "present",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Attendance.objects.filter(student=self.profile_a, weekly_lesson=lesson).exists()
        )

    def test_admin_overlapping_term_shows_error(self):
        response = self._post(
            "admin:academics_term_add",
            [],
            {
                "code": "t-overlap",
                "name": "Пересекающийся",
                "start_date": "2026-10-01",
                "end_date": "2027-03-31",
                "session_start": "2027-01-10",
                "session_end": "2027-01-31",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Term.objects.filter(code="t-overlap").exists())

    def test_admin_mark_without_date_shows_error(self):
        before = CurrentMark.objects.count()
        response = self._post(
            "admin:academics_currentmark_add",
            [],
            {
                "student": self.profile_a.pk,
                "curriculum_item": self.item_a.pk,
                "value": 5,
                "kind": "Семинар",
                "date": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CurrentMark.objects.count(), before)

    def test_admin_attendance_without_student_shows_error(self):
        lesson = make_lesson(
            [self.group_x],
            0,
            2,
            make_room("room-303"),
            valid_from=date(2026, 9, 1),
            valid_until=date(2026, 12, 31),
        )
        response = self._post(
            "admin:academics_attendance_add",
            [],
            {
                "student": "",
                "weekly_lesson": lesson.pk,
                "original_date": "2026-11-16",
                "status": "present",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Attendance.objects.filter(weekly_lesson=lesson).exists())

    def test_admin_attendance_without_lesson_shows_error(self):
        response = self._post(
            "admin:academics_attendance_add",
            [],
            {
                "student": self.profile_a.pk,
                "weekly_lesson": "",
                "original_date": "2026-11-16",
                "status": "present",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Attendance.objects.filter(student=self.profile_a).exists())


class QueryCountTests(AccessFixture):
    def test_student_page_constant_queries(self):
        with mock.patch("django.utils.timezone.now", return_value=aware(NOW)):
            self.client.force_login(self.student_a)
            self.client.get("/grades/")
            with CaptureQueriesContext(connection) as ctx:
                self.client.get("/grades/")
        count1 = len(ctx.captured_queries)

        # add more data
        for i in range(3):
            item = make_item(self.group_x, make_discipline(f"Дисциплина-Доп-{i}"), self.term)
            for k in range(4):
                make_mark(self.profile_a, item, 4, date(2026, 10, 1 + k))
            make_result(self.profile_a, item, "4", date=date(2026, 10, 5))
        with mock.patch("django.utils.timezone.now", return_value=aware(NOW)):
            self.client.force_login(self.student_a)
            with CaptureQueriesContext(connection) as ctx2:
                self.client.get("/grades/")
        count2 = len(ctx2.captured_queries)
        self.assertEqual(count2, count1)

    def test_staff_page_constant_queries(self):
        url = reverse("academics:staff_student_grades", args=[self.profile_a.pk])
        with mock.patch("django.utils.timezone.now", return_value=aware(NOW)):
            self.client.force_login(self.staff_x)
            self.client.get(url)
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(url)
        count1 = len(ctx.captured_queries)

        for i in range(3):
            item = make_item(self.group_x, make_discipline(f"Дисциплина-Доп-{i}"), self.term)
            for k in range(4):
                make_mark(self.profile_a, item, 4, date(2026, 10, 1 + k))
            make_result(self.profile_a, item, "4", date=date(2026, 10, 5))
        with mock.patch("django.utils.timezone.now", return_value=aware(NOW)):
            self.client.force_login(self.staff_x)
            with CaptureQueriesContext(connection) as ctx2:
                self.client.get(url)
        count2 = len(ctx2.captured_queries)
        self.assertEqual(count2, count1)
