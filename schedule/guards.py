"""Change guard registry: lets other apps veto schedule changes without schedule importing them."""

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import LessonChange

ChangeGuard = Callable[["LessonChange", bool], list[str]]

_guards: list[ChangeGuard] = []


def register_change_guard(guard: ChangeGuard) -> None:
    """Append ``guard`` if it is not already registered (idempotent)."""
    if guard not in _guards:
        _guards.append(guard)


def run_change_guards(change: "LessonChange", *, deleting: bool) -> list[str]:
    """Run all registered guards in registration order and concatenate their messages."""
    errors: list[str] = []
    for guard in _guards:
        errors.extend(guard(change, deleting))
    return errors
