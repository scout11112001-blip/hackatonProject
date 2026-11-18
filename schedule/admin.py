from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse

from .forms import WeeklyLessonAdminForm
from .models import LessonChange, WeeklyLesson
from .mutations import delete_lesson_change


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
    readonly_fields = ("seed_key", "changed_at")

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

    def delete_model(self, request, obj):
        delete_lesson_change(obj)

    def delete_view(self, request, object_id, extra_context=None):
        try:
            with transaction.atomic():
                return super().delete_view(request, object_id, extra_context)
        except ValidationError as exc:
            self.message_user(request, " ".join(exc.messages), level=messages.ERROR)
            return HttpResponseRedirect(
                reverse("admin:schedule_lessonchange_change", args=[object_id])
            )
