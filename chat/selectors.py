"""Querysets for the chat app.

Every dialog lookup must go through ``dialogs_visible_to`` so that a student
sees only their own dialog and staff see only dialogs of students in their
faculty.
"""

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db.models import Case, Count, F, IntegerField, Q, QuerySet, Value, When

from accounts.models import User
from accounts.selectors import students_visible_to

from .constants import STAFF_LIST_LIMIT
from .models import AuthorRole, Dialog, Message


def dialogs_visible_to(user: AbstractBaseUser | AnonymousUser) -> QuerySet[Dialog]:
    if not user.is_authenticated or not user.is_active:
        return Dialog.objects.none()
    if user.role == User.Role.STAFF:
        return Dialog.objects.filter(student__in=students_visible_to(user))
    if user.role == User.Role.STUDENT:
        return Dialog.objects.filter(student__user_id=user.pk)
    return Dialog.objects.none()


def staff_dialog_list(user: AbstractBaseUser | AnonymousUser) -> QuerySet[Dialog]:
    return (
        dialogs_visible_to(user)
        .select_related("student__group")
        .annotate(
            unread=Count(
                "messages",
                filter=Q(
                    messages__author_role=AuthorRole.STUDENT,
                    messages__id__gt=F("staff_read_id"),
                ),
            )
        )
        .annotate(
            has_unread=Case(
                When(unread__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField()
            )
        )
        .order_by("has_unread", F("last_message_at").desc(nulls_last=True), "-pk")[
            :STAFF_LIST_LIMIT
        ]
    )


def student_unread_count(user: AbstractBaseUser | AnonymousUser) -> int:
    if not user.is_authenticated or not user.is_active or user.role != User.Role.STUDENT:
        return 0
    return Message.objects.filter(
        dialog__student__user_id=user.pk,
        author_role=AuthorRole.STAFF,
        id__gt=F("dialog__student_read_id"),
    ).count()
