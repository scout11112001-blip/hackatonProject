"""Test clock helpers.

A plain module (not a test module). It freezes ``django.utils.timezone.now`` for a
whole test class so tests do not depend on the real current date.
"""

from datetime import datetime
from typing import ClassVar
from unittest import mock
from zoneinfo import ZoneInfo

MOSCOW = ZoneInfo("Europe/Moscow")


def moscow(dt_str: str) -> datetime:
    """Parse an ISO string as a Moscow-aware datetime, e.g. "2026-11-18 12:00"."""
    return datetime.fromisoformat(dt_str).replace(tzinfo=MOSCOW)


class FrozenClockMixin:
    frozen_now: ClassVar[str] = "2026-11-18 12:00"

    @classmethod
    def setUpClass(cls) -> None:
        cls._clock_patcher = mock.patch(
            "django.utils.timezone.now", return_value=moscow(cls.frozen_now)
        )
        cls._clock_patcher.start()
        try:
            super().setUpClass()
        except Exception:
            cls._clock_patcher.stop()
            raise

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            super().tearDownClass()
        finally:
            cls._clock_patcher.stop()
