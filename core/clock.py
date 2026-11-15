"""Call-time clock for model defaults (test clock patches apply)."""

from datetime import datetime

from django.utils import timezone


def now() -> datetime:
    return timezone.now()
