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


def staff_unread_count(user: AbstractBaseUser | AnonymousUser) -> int:
    """Unread student messages in the dialogs this staff member can see (TASK-018).

    Same rule as the "new" count of ``staff_dialog_list``: student messages after the shared
    read marker ``staff_read_id``. The dialog filter is the rule of ``dialogs_visible_to``
    (active students of the staff member's faculty) written as joins, so the menu badge is one
    COUNT query on every page; ``StaffUnreadCountTests.test_matches_visibility_rule`` keeps
    the two in step.
    """
    if not user.is_authenticated or not user.is_active or user.role != User.Role.STAFF:
        return 0
    return Message.objects.filter(
        dialog__student__group__program__faculty__staff_members__user_id=user.pk,
        dialog__student__user__is_active=True,
        author_role=AuthorRole.STUDENT,
        id__gt=F("dialog__staff_read_id"),
    ).count()


def chat_unread_count(user: AbstractBaseUser | AnonymousUser) -> int:
    """Count for the "Чат (n)" / "Чаты (n)" menu item; 0 for every other role."""
    if not user.is_authenticated or not user.is_active:
        return 0
    if user.role == User.Role.STUDENT:
        return student_unread_count(user)
    if user.role == User.Role.STAFF:
        return staff_unread_count(user)
    return 0
