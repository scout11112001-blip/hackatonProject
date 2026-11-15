"""Queryset scoping for announcements."""

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, QuerySet

from accounts.models import StudentProfile, User

from .models import Announcement, Audience


def announcements_for_student(student: StudentProfile) -> QuerySet[Announcement]:
    faculty_id = student.group.program.faculty_id
    return Announcement.objects.filter(is_published=True).filter(
        Q(audience=Audience.UNIVERSITY)
        | Q(audience=Audience.FACULTY, faculty_id=faculty_id)
        | Q(audience=Audience.GROUP, group_id=student.group_id)
    )


def announcements_managed_by(user: AbstractBaseUser | AnonymousUser) -> QuerySet[Announcement]:
    if not user.is_authenticated or not user.is_active or user.role != User.Role.STAFF:
        return Announcement.objects.none()
    try:
        profile = user.staff_profile
    except ObjectDoesNotExist:
        return Announcement.objects.none()
    return Announcement.objects.filter(
        Q(audience=Audience.FACULTY, faculty_id=profile.faculty_id)
        | Q(audience=Audience.GROUP, group__program__faculty_id=profile.faculty_id)
    )
