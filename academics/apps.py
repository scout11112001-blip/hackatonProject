from django.apps import AppConfig


class AcademicsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "academics"
    verbose_name = "Успеваемость"

    def ready(self):
        from schedule.guards import register_change_guard

        from .services import attendance_change_guard

        register_change_guard(attendance_change_guard)
