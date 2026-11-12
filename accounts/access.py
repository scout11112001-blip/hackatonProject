"""Role checks and view guards.

Every function here decides whether ``request.user`` may act in a role and
returns the matching profile, raising ``PermissionDenied`` on any failure.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, ClassVar, TypeVar

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import HttpRequest, HttpResponse

from .models import StaffProfile, StudentProfile, User

ViewFunc = TypeVar("ViewFunc", bound=Callable[..., HttpResponse])


def get_profile_for_role(
    user: AbstractBaseUser | AnonymousUser, role: str
) -> StudentProfile | StaffProfile:
    if role not in (User.Role.STUDENT, User.Role.STAFF):
        raise ValueError
    if not user.is_authenticated or not user.is_active:
        raise PermissionDenied
    if user.role != role:
        raise PermissionDenied
    attr = "student_profile" if role == User.Role.STUDENT else "staff_profile"
    try:
        return getattr(user, attr)
    except ObjectDoesNotExist:
        raise PermissionDenied from None


class RoleRequiredMixin:
    required_role: ClassVar[str]

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.profile = get_profile_for_role(request.user, self.required_role)
        return super().dispatch(request, *args, **kwargs)


class StudentRequiredMixin(RoleRequiredMixin):
    required_role = User.Role.STUDENT


class StaffRequiredMixin(RoleRequiredMixin):
    required_role = User.Role.STAFF


def role_required(role: str) -> Callable[[ViewFunc], ViewFunc]:
    def decorator(view_func: ViewFunc) -> ViewFunc:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            request.profile = get_profile_for_role(request.user, role)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
