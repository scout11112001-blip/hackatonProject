from typing import Any

from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_variables

from .throttling import get_client_ip, is_locked, register_failure, reset_failures


class ThrottledLoginFormMixin:
    error_messages = {
        **AuthenticationForm.error_messages,
        "locked": "Слишком много неудачных попыток входа. Попробуйте позже.",
    }

    @method_decorator(sensitive_variables())
    def clean(self) -> dict[str, Any]:
        username = self.cleaned_data.get("username") or ""
        ip = get_client_ip(self.request)
        now = timezone.now()
        if username and is_locked(username, ip, now):
            raise ValidationError(self.error_messages["locked"], code="locked")
        try:
            cleaned = super().clean()
        except ValidationError:
            if username:
                register_failure(username, ip, now)
            raise
        if username:
            reset_failures(username, ip)
        return cleaned


class ThrottledAuthenticationForm(ThrottledLoginFormMixin, AuthenticationForm):
    pass


class ThrottledAdminAuthenticationForm(ThrottledLoginFormMixin, AdminAuthenticationForm):
    pass
