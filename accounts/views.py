from typing import Any

from django.contrib.auth.views import LoginView
from django.db.models import QuerySet
from django.views.generic import DetailView, ListView, TemplateView

from .access import StaffRequiredMixin
from .models import StaffProfile, StudentProfile
from .selectors import students_visible_to


class DeaneryLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class ProfileView(TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["student_profile"] = (
            StudentProfile.objects.select_related("group__program__faculty")
            .filter(user=user)
            .first()
            if user.is_student
            else None
        )
        context["staff_profile"] = (
            StaffProfile.objects.select_related("faculty").filter(user=user).first()
            if user.is_deanery_staff
            else None
        )
        return context


class StaffStudentListView(StaffRequiredMixin, ListView):
    template_name = "accounts/student_list.html"
    context_object_name = "students"

    def get_queryset(self) -> QuerySet[StudentProfile]:
        return students_visible_to(self.request.user)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["faculty"] = self.profile.faculty
        return context


class StaffStudentDetailView(StaffRequiredMixin, DetailView):
    template_name = "accounts/student_detail.html"
    context_object_name = "student"

    def get_queryset(self) -> QuerySet[StudentProfile]:
        return students_visible_to(self.request.user)
