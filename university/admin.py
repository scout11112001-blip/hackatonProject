from django.contrib import admin

from .models import Discipline, Faculty, Program, Room, StudyGroup, Teacher


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "faculty")
    list_filter = ("faculty",)
    search_fields = ("code", "name")


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "program", "course")
    list_filter = ("course", "program__faculty")
    search_fields = ("name",)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("number", "floor", "code")
    list_filter = ("floor",)
    search_fields = ("number", "code")


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("full_name", "title")
    search_fields = ("last_name", "first_name")


@admin.register(Discipline)
class DisciplineAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name")
    search_fields = ("name", "short_name")
