"""Login brute-force throttling keyed by (normalized username, client IP)."""

import ipaddress
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest

from .models import LoginThrottle

# Sentinel for "client IP unknown"; not a bind address.
UNKNOWN_IP = "0.0.0.0"  # noqa: S104


def normalize_username(username: str) -> str:
    return username.strip().casefold()[:150]


def get_client_ip(request: HttpRequest | None) -> str:
    if request is None:
        return UNKNOWN_IP
    header = settings.CLIENT_IP_HEADER
    candidate = ""
    if header == "HTTP_X_REAL_IP":
        candidate = request.META.get(header, "").strip()
    elif header == "HTTP_X_FORWARDED_FOR":
        raw = request.META.get(header, "")
        if raw:
            candidate = raw.split(",")[-1].strip()
    if candidate:
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            pass
    remote = request.META.get("REMOTE_ADDR", "")
    try:
        ipaddress.ip_address(remote)
        return remote
    except ValueError:
        return UNKNOWN_IP


def is_locked(username: str, ip: str, now: datetime) -> bool:
    return LoginThrottle.objects.filter(
        username_key=normalize_username(username), ip_address=ip, locked_until__gt=now
    ).exists()


def register_failure(username: str, ip: str, now: datetime) -> None:
    key = normalize_username(username)
    window = timedelta(seconds=settings.LOGIN_LOCKOUT_SECONDS)
    with transaction.atomic():
        # Opportunistic cleanup of expired rows (personal data, retained <= ~1 day).
        stale_ts = now - max(window, timedelta(days=1))
        LoginThrottle.objects.filter(
            last_failure_at__lt=stale_ts, locked_until__isnull=True
        ).delete()
        LoginThrottle.objects.filter(locked_until__lt=now - timedelta(days=1)).delete()

        row, _ = LoginThrottle.objects.get_or_create(
            username_key=key,
            ip_address=ip,
            defaults={"first_failure_at": now, "last_failure_at": now},
        )
        row = LoginThrottle.objects.select_for_update().get(pk=row.pk)
        if (row.locked_until is not None and row.locked_until <= now) or (
            row.first_failure_at <= now - window
        ):
            row.failures = 0
            row.first_failure_at = now
            row.locked_until = None
        row.failures += 1
        row.last_failure_at = now
        if row.failures >= settings.LOGIN_FAILURE_LIMIT:
            row.locked_until = now + window
        row.save()


def reset_failures(username: str, ip: str) -> None:
    LoginThrottle.objects.filter(username_key=normalize_username(username), ip_address=ip).delete()
