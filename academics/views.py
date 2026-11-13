from datetime import date
from typing import Any

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from academics.models import Term
from academics.services import current_term, student_overview, student_term_report, student_terms
from accounts.access import StaffRequiredMixin, StudentRequiredMixin
from accounts.models import StudentProfile
from accounts.selectors import students_visible_to


class StudentGradesView(StudentRequiredMixin, TemplateView):
    template_name = "academics/report.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        student = self.profile
        context.update(
            _report_context(
                student,
                today,
                self.kwargs.get("term_code"),
                url_name="academics:my_grades_term",
                url_kwargs={},
            )
        )
        context["is_staff_view"] = False
        return context


class StaffStudentGradesView(StaffRequiredMixin, TemplateView):
    template_name = "academics/report.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        student = get_object_or_404(students_visible_to(self.request.user), pk=self.kwargs["pk"])
        today = timezone.localdate()
        context.update(
            _report_context(
                student,
                today,
                self.kwargs.get("term_code"),
                url_name="academics:staff_student_grades_term",
                url_kwargs={"pk": student.pk},
            )
        )
        context["is_staff_view"] = True
        context["student"] = student
        context["back_url"] = reverse("accounts:staff_student_detail", args=[student.pk])
        return context


def _report_context(
    student: StudentProfile,
    today: date,
    term_code: str | None,
    url_name: str,
    url_kwargs: dict[str, Any],
) -> dict[str, Any]:
    terms = student_terms(student)
    if term_code:
        term = get_object_or_404(Term, code=term_code)
    else:
        term = current_term(today)
    report = student_term_report(student, term, today) if term else None

    selector = list(terms)
    if term is not None and term not in selector:
        selector.append(term)
    selector.sort(key=lambda t: t.start_date, reverse=True)

    term_links = [
        {
            "term": t,
            "url": reverse(url_name, kwargs={**url_kwargs, "term_code": t.code}),
            "is_selected": t == term,
        }
        for t in selector
    ]

    return {
        "overview": student_overview(student, today),
        "term": term,
        "report": report,
        "term_links": term_links,
        "today": today,
    }
