from django.urls import path, register_converter

from . import views
from .converters import IsoDateConverter

register_converter(IsoDateConverter, "isodate")

app_name = "schedule"
urlpatterns = [
    path("schedule/", views.TodayView.as_view(), name="today"),
    path("schedule/week/", views.StudentWeekView.as_view(), name="week"),
    path("schedule/week/<isodate:day>/", views.StudentWeekView.as_view(), name="week_of"),
    path("staff/schedule/", views.StaffGroupListView.as_view(), name="staff_groups"),
    path(
        "staff/schedule/<int:group_id>/",
        views.StaffGroupWeekView.as_view(),
        name="staff_group_week",
    ),
    path(
        "staff/schedule/<int:group_id>/<isodate:day>/",
        views.StaffGroupWeekView.as_view(),
        name="staff_group_week_of",
    ),
]
