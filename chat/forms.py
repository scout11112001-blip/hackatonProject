from django import forms

from .constants import MESSAGE_MAX_LENGTH
from .services import normalize_text, text_errors


class MessageForm(forms.Form):
    text = forms.CharField(
        label="Сообщение",
        strip=False,
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": MESSAGE_MAX_LENGTH}),
    )
    client_token = forms.UUIDField(required=False, widget=forms.HiddenInput)

    def clean_text(self):
        text = normalize_text(self.cleaned_data["text"])
        errors = text_errors(text)
        if errors:
            raise forms.ValidationError(errors)
        return text
