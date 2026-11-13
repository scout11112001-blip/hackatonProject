from django.contrib import admin

from .forms import WeeklyLessonAdminForm
from .models import LessonChange, WeeklyLesson


@admin.register(WeeklyLesson)
class WeeklyLessonAdmin(admin.ModelAdmin):
    form = WeeklyLessonAdminForm
    list_display = (
        "weekday",
        "slot",
        "discipline",
        "lesson_type",
        "teacher",
        "room",
        "group_names",
        "valid_from",
        "valid_until",
    )
    list_filter = ("weekday", "lesson_type", "groups")
    filter_horizontal = ("groups",)
    list_select_related = ("discipline", "teacher", "room")
    readonly_fields = ("seed_key",)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("groups")

    @admin.display(description="группы")
    def group_names(self, obj):
        return ", ".join(g.name for g in obj.groups.all())


@admin.register(LessonChange)
class LessonChangeAdmin(admin.ModelAdmin):
    list_display = (
        "original_date",
        "kind",
        "weekly_lesson",
        "new_date",
        "new_slot",
        "new_room",
        "new_teacher",
        "reason",
    )
    list_filter = ("kind",)
    date_hierarchy = "original_date"
    list_select_related = ("weekly_lesson__discipline", "new_room", "new_teacher")
    readonly_fields = ("seed_key",)
