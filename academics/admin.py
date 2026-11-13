from django.contrib import admin

from .models import Attendance, CurrentMark, CurriculumItem, FinalResult, Term


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "start_date", "end_date", "session_start", "session_end")
    search_fields = ("code", "name")


@admin.register(CurriculumItem)
class CurriculumItemAdmin(admin.ModelAdmin):
    list_display = ("discipline", "group", "term", "assessment_form", "credits")
    list_filter = ("term", "group", "assessment_form")
    list_select_related = ("discipline", "group", "term")
    search_fields = ("discipline__name", "group__name")


@admin.register(CurrentMark)
class CurrentMarkAdmin(admin.ModelAdmin):
    list_display = ("student", "curriculum_item", "value", "date", "kind")
    list_filter = ("curriculum_item__term",)
    readonly_fields = ("seed_key",)
    list_select_related = ("student", "curriculum_item__discipline")
    search_fields = ("student__last_name", "curriculum_item__discipline__name")


@admin.register(FinalResult)
class FinalResultAdmin(admin.ModelAdmin):
    list_display = ("student", "curriculum_item", "attempt", "result", "date")
    list_filter = ("curriculum_item__term", "result")
    list_select_related = ("student", "curriculum_item__discipline")
    search_fields = ("student__last_name", "curriculum_item__discipline__name")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "weekly_lesson", "original_date", "status")
    list_filter = ("status",)
    date_hierarchy = "original_date"
    list_select_related = ("student", "weekly_lesson__discipline")
    search_fields = ("student__last_name", "weekly_lesson__discipline__name")
