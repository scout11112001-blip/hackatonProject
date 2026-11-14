"""Forms for petitions."""

from django import forms

from petitions.files import validate_attachments
from petitions.models import MAX_COMMENT_LENGTH, PetitionStatus, RequestType


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": "application/pdf,.pdf"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []
        items = data if isinstance(data, (list, tuple)) else [data]
        return [super().clean(item, initial) for item in items]


class PetitionForm(forms.Form):
    comment = forms.CharField(
        label="Комментарий",
        required=False,
        max_length=MAX_COMMENT_LENGTH,
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    files = MultipleFileField(
        label="PDF-файлы (необязательно, до 3 файлов по 5 МБ)", required=False
    )

    def __init__(self, *args, request_type: RequestType, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_type = request_type
        self.fields["comment"].required = request_type.comment_required
        self.fields["comment"].help_text = request_type.comment_hint

    def clean_comment(self):
        comment = (self.cleaned_data.get("comment") or "").strip()
        if self.request_type.comment_required and not comment:
            raise forms.ValidationError("Для этой заявки комментарий обязателен.")
        return comment

    def clean_files(self):
        files = self.cleaned_data.get("files") or []
        validate_attachments(files)
        return files


class TransitionForm(forms.Form):
    expected_status = forms.ChoiceField(choices=PetitionStatus.choices)
    new_status = forms.ChoiceField(choices=PetitionStatus.choices)
    comment = forms.CharField(required=False, max_length=MAX_COMMENT_LENGTH)


class StaffCommentForm(forms.Form):
    text = forms.CharField(
        label="Комментарий",
        max_length=MAX_COMMENT_LENGTH,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
