"""Queryset scoping for petitions.

Every lookup must start from ``petitions_visible_to`` / ``attachments_visible_to``.
"""

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet

from accounts.models import User
from petitions.models import Petition, PetitionAttachment


def petitions_visible_to(
    user: AbstractBaseUser | AnonymousUser,
) -> QuerySet[Petition]:
    qs: QuerySet[Petition] = Petition.objects.select_related(
        "request_type", "student__group__program__faculty"
    )
    if not user.is_authenticated or not user.is_active:
        return qs.none()
    if user.role == User.Role.STAFF:
        try:
            profile = user.staff_profile
        except ObjectDoesNotExist:
            return qs.none()
        return qs.filter(student__group__program__faculty=profile.faculty)
    if user.role == User.Role.STUDENT:
        if getattr(user, "student_profile", None) is None:
            return qs.none()
        return qs.filter(student__user=user)
    return qs.none()


def attachments_visible_to(
    user: AbstractBaseUser | AnonymousUser,
) -> QuerySet[PetitionAttachment]:
    return PetitionAttachment.objects.filter(petition__in=petitions_visible_to(user))
