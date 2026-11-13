from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .forms import ThrottledAdminAuthenticationForm
from .models import LoginThrottle, StaffProfile, StudentProfile, User

admin.site.login_form = ThrottledAdminAuthenticationForm


class UserCreationAdminForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("username", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].required = True


class UserChangeAdminForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeAdminForm
    add_form = UserCreationAdminForm
    list_display = ("username", "role", "is_active", "is_superuser", "last_login")
    list_filter = ("role", "is_active", "is_superuser")
    fieldsets = BaseUserAdmin.fieldsets + (("Роль", {"fields": ("role",)}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (("Роль", {"fields": ("role",)}),)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "group", "record_number", "user")
    list_filter = ("group__program__faculty", "group")
    search_fields = ("last_name", "first_name", "record_number", "user__username")
    list_select_related = ("group", "user")


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "position", "faculty", "user")
    list_filter = ("faculty",)
    search_fields = ("last_name", "first_name", "user__username")


@admin.register(LoginThrottle)
class LoginThrottleAdmin(admin.ModelAdmin):
    list_display = (
        "username_key",
        "ip_address",
        "failures",
        "locked_until",
        "last_failure_at",
    )
    search_fields = ("username_key", "ip_address")
    readonly_fields = (
        "username_key",
        "ip_address",
        "failures",
        "first_failure_at",
        "last_failure_at",
        "locked_until",
    )

    def has_add_permission(self, request):
        return False
