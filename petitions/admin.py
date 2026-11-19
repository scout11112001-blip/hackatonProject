from django.contrib import admin

from .models import Petition, PetitionAttachment, PetitionComment, PetitionStatusChange, RequestType


@admin.register(RequestType)
class RequestTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "kind",
        "processing_days",
        "comment_required",
        "subject_required",
        "is_active",
    )
    list_filter = ("kind", "is_active")


class PetitionHistoryInline(admin.TabularInline):
    model = PetitionStatusChange
    extra = 0
    can_delete = False
    fields = ("from_status", "to_status", "actor", "created_at", "comment")
    readonly_fields = ("from_status", "to_status", "actor", "created_at", "comment")

    def has_add_permission(self, request, obj=None):
        return False


class PetitionCommentInline(admin.TabularInline):
    model = PetitionComment
    extra = 0
    can_delete = False
    fields = ("author", "created_at", "text")
    readonly_fields = ("author", "created_at", "text")

    def has_add_permission(self, request, obj=None):
        return False


class PetitionAttachmentInline(admin.TabularInline):
    model = PetitionAttachment
    extra = 0
    can_delete = False
    fields = ("original_name", "size", "uploaded_at")
    readonly_fields = ("original_name", "size", "uploaded_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Petition)
class PetitionAdmin(admin.ModelAdmin):
    list_display = ("public_id", "request_type", "subject", "student", "status", "created_at")
    list_filter = ("status", "request_type")
    inlines = [PetitionHistoryInline, PetitionCommentInline, PetitionAttachmentInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
