"""Queryset scoping for student data.

Every student-data lookup must start from ``students_visible_to``. Never look
up a ``StudentProfile`` by a raw primary key without it.
"""

from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet

from university.models import StudyGroup

from .models import StudentProfile, User


def students_visible_to(
    user: AbstractBaseUser | AnonymousUser,
) -> QuerySet[StudentProfile]:
    qs: QuerySet[StudentProfile] = StudentProfile.objects.select_related(
        "user", "group__program__faculty"
    )
    if not user.is_authenticated or not user.is_active:
        return qs.none()
    if user.role == User.Role.STAFF:
        try:
            profile: Any = user.staff_profile
        except ObjectDoesNotExist:
            return qs.none()
        return qs.filter(group__program__faculty=profile.faculty, user__is_active=True)
    if user.role == User.Role.STUDENT:
        return qs.filter(user=user)
    return qs.none()


def groups_visible_to(
    user: AbstractBaseUser | AnonymousUser,
) -> QuerySet[StudyGroup]:
    qs: QuerySet[StudyGroup] = StudyGroup.objects.select_related("program__faculty")
    if not user.is_authenticated or not user.is_active:
        return qs.none()
    if user.role == User.Role.STAFF:
        try:
            profile: Any = user.staff_profile
        except ObjectDoesNotExist:
            return qs.none()
        return qs.filter(program__faculty=profile.faculty)
    if user.role == User.Role.STUDENT:
        try:
            profile: Any = user.student_profile
        except ObjectDoesNotExist:
            return qs.none()
        return qs.filter(pk=profile.group_id)
    return qs.none()
