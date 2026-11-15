from collections.abc import Sequence
from datetime import date

from django import forms

from university.models import Faculty, StudyGroup

from .constants import BODY_MAX_LENGTH, TARGET_FACULTY, TARGET_GROUP_PREFIX, TITLE_MAX_LENGTH
from .models import Audience
from .services import deadline_errors


class AnnouncementForm(forms.Form):
    title = forms.CharField(label="Заголовок", max_length=TITLE_MAX_LENGTH)
    body = forms.CharField(
        label="Текст", max_length=BODY_MAX_LENGTH, widget=forms.Textarea(attrs={"rows": 6})
    )
    target = forms.ChoiceField(label="Кому")
    deadline = forms.DateField(
        label="Срок (необязательно)",
        required=False,
        help_text="Последний день, включительно.",
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )

    def __init__(
        self,
        *args,
        faculty: Faculty,
        groups: Sequence[StudyGroup],
        today: date,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.today = today
        self._groups = {f"{TARGET_GROUP_PREFIX}{g.pk}": g for g in groups}
        self.fields["target"].choices = [(TARGET_FACULTY, f"Весь факультет: {faculty.name}")] + [
            (key, f"Группа {g.name}") for key, g in self._groups.items()
        ]

    def clean_deadline(self):
        value = self.cleaned_data.get("deadline")
        errors = deadline_errors(value, self.today)
        if errors:
            raise forms.ValidationError(errors)
        return value

    def clean(self):
        cleaned = super().clean()
        target = cleaned.get("target")
        if target == TARGET_FACULTY:
            cleaned["audience"] = Audience.FACULTY
            cleaned["group"] = None
        elif target in self._groups:
            cleaned["audience"] = Audience.GROUP
            cleaned["group"] = self._groups[target]
        return cleaned
