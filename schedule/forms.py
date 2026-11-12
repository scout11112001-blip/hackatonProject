from typing import Any

from django import forms

from .models import WeeklyLesson
from .validation import validate_weekly_lesson


class WeeklyLessonAdminForm(forms.ModelForm):
    class Meta:
        model = WeeklyLesson
        fields = [
            "weekday",
            "slot",
            "discipline",
            "lesson_type",
            "teacher",
            "room",
            "groups",
            "valid_from",
            "valid_until",
        ]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        required = ["weekday", "slot", "valid_from", "valid_until", "room", "groups"]
        if any(f not in cleaned for f in required):
            return cleaned
        errors = validate_weekly_lesson(
            weekday=cleaned["weekday"],
            slot=cleaned["slot"],
            valid_from=cleaned["valid_from"],
            valid_until=cleaned["valid_until"],
            room_id=cleaned["room"].pk,
            group_ids=[g.pk for g in cleaned["groups"]],
            exclude_pk=self.instance.pk,
        )
        for msg in errors:
            self.add_error(None, msg)
        return cleaned
