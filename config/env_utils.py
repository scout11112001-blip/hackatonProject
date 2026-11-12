"""Environment helpers for the deanery project settings.

Pure functions only. This module must not import ``django.conf.settings``,
so that it can be unit-tested without a configured Django environment.
"""

import re

from django.core.exceptions import ImproperlyConfigured

DEV_SECRET_KEY = "django-insecure-dev-only-key-do-not-use-in-production"


def resolve_secret_key(raw: str, debug: bool) -> str:
    """Return the secret key, failing fast in production when it is missing."""
    value = raw.strip()
    if value:
        return value
    if debug:
        return DEV_SECRET_KEY
    raise ImproperlyConfigured("SECRET_KEY environment variable is required when DEBUG is false.")


def resolve_admin_url(raw: str, debug: bool) -> str:
    """Return a validated URL prefix for Django admin, e.g. ``"staff-panel/"``."""
    value = raw.strip().strip("/")
    if value == "":
        if debug:
            return "admin/"
        raise ImproperlyConfigured(
            "ADMIN_URL environment variable is required when DEBUG is false."
        )
    if not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", value):
        raise ImproperlyConfigured("ADMIN_URL may contain only letters, digits, '-', '_' and '/'.")
    return value + "/"
