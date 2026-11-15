from django.contrib import admin

from .models import Dialog, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False
    fields = readonly_fields = ("created_at", "author_role", "author", "text")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Dialog)
class DialogAdmin(admin.ModelAdmin):
    list_display = ("student", "last_message_at", "student_read_id", "staff_read_id")
    list_select_related = ("student",)
    inlines = [MessageInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
