from datetime import date, timedelta
from typing import Any

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView, TemplateView

from accounts.access import StaffRequiredMixin, StudentRequiredMixin
from accounts.selectors import groups_visible_to
from schedule.services import (
    WeekSchedule,
    today_schedule,
    week_schedule,
    week_start,
)
from university.models import StudyGroup


class TodayView(StudentRequiredMixin, TemplateView):
    template_name = "schedule/today.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        day, annotation = today_schedule(self.profile.group_id, timezone.now())
        context["day"] = day
        context["annotation"] = annotation
        context["group"] = self.profile.group
        context["week_url"] = reverse("schedule:week")
        return context


class StudentWeekView(StudentRequiredMixin, TemplateView):
    template_name = "schedule/week.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        day = self.kwargs.get("day") or today
        week = week_schedule(day, [self.profile.group_id], today)
        context.update(_week_context(week, today, "schedule:week_of", {}))
        context["group"] = self.profile.group
        context["title"] = "Моё расписание"
        return context


class StaffGroupListView(StaffRequiredMixin, ListView):
    template_name = "schedule/staff_group_list.html"
    context_object_name = "groups"

    def get_queryset(self) -> QuerySet[StudyGroup]:
        return groups_visible_to(self.request.user)


class StaffGroupWeekView(StaffRequiredMixin, TemplateView):
    template_name = "schedule/week.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        group = get_object_or_404(groups_visible_to(self.request.user), pk=self.kwargs["group_id"])
        today = timezone.localdate()
        day = self.kwargs.get("day") or today
        week = week_schedule(day, [group.pk], today)
        context.update(
            _week_context(week, today, "schedule:staff_group_week_of", {"group_id": group.pk})
        )
        context["group"] = group
        context["title"] = f"Расписание группы {group.name}"
        context["back_url"] = reverse("schedule:staff_groups")
        return context


def _week_context(
    week: WeekSchedule, today: date, url_name: str, url_kwargs: dict[str, Any]
) -> dict[str, Any]:
    return {
        "week": week,
        "prev_url": reverse(url_name, kwargs={**url_kwargs, "day": week.start - timedelta(days=7)}),
        "next_url": reverse(url_name, kwargs={**url_kwargs, "day": week.start + timedelta(days=7)}),
        "current_url": reverse(url_name, kwargs={**url_kwargs, "day": today}),
        "is_current_week": week.start == week_start(today),
    }
