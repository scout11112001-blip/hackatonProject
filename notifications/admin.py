from django.contrib import admin
from django.utils import timezone

from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "audience",
        "faculty",
        "group",
        "deadline",
        "is_published",
        "published_at",
    )
    list_filter = ("audience", "is_published")
    search_fields = ("title",)
    list_select_related = ("faculty", "group")
    fields = (
        "title",
        "body",
        "audience",
        "faculty",
        "group",
        "deadline",
        "is_published",
        "author",
        "published_at",
        "unpublished_at",
        "unpublished_by",
    )
    readonly_fields = ("author", "published_at", "unpublished_at", "unpublished_by")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        if "is_published" in form.changed_data or not change:
            if obj.is_published:
                obj.unpublished_at = None
                obj.unpublished_by = None
            else:
                obj.unpublished_at = timezone.now()
                obj.unpublished_by = request.user
        super().save_model(request, obj, form, change)
