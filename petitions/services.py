"""Petition services: submission, status transitions, staff comments."""

from datetime import date, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.access import get_profile_for_role
from accounts.models import StudentProfile, User
from core import clock
from core.storage import get_private_storage
from petitions.files import store_attachment, validate_attachments
from petitions.models import (
    MAX_COMMENT_LENGTH,
    Petition,
    PetitionComment,
    PetitionStatus,
    PetitionStatusChange,
)
from petitions.workflow import COMMENT_REQUIRED_FOR, OPEN_STATUSES, SUBMITTED, can_transition

MAX_OPEN_PER_TYPE = 3


class StaleStatusError(ValidationError):
    default_message = "Заявка уже изменена, обновите страницу."


def _status_label(status: str) -> str:
    return dict(PetitionStatus.choices)[status]


def add_working_days(start: date, days: int) -> date:
    if days < 1:
        raise ValueError("days must be positive")
    d = start
    remaining = days
    while remaining > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            remaining -= 1
    return d


def _lock_student(pk: int) -> None:
    StudentProfile.objects.select_for_update().filter(pk=pk).values_list("pk", flat=True).get()


def _lock_petition(pk: int) -> Petition:
    return Petition.objects.select_for_update().select_related("student__group__program").get(pk=pk)


def submit_petition(
    student: StudentProfile,
    request_type: object,
    comment: str,
    uploads: list,
) -> Petition:
    comment = (comment or "").strip()
    errors: list[str] = []
    if not request_type.is_active:
        errors.append("Этот вид заявки сейчас недоступен.")
    if len(comment) > MAX_COMMENT_LENGTH:
        errors.append("Комментарий слишком длинный.")
    if request_type.comment_required and not comment:
        errors.append("Для этой заявки комментарий обязателен.")
    try:
        validate_attachments(uploads)
    except ValidationError as exc:
        errors.extend(exc.messages)
    if errors:
        raise ValidationError(errors)

    stored: list[str] = []
    try:
        with transaction.atomic():
            _lock_student(student.pk)
            open_count = Petition.objects.filter(
                student=student, request_type=request_type, status__in=OPEN_STATUSES
            ).count()
            if open_count >= MAX_OPEN_PER_TYPE:
                raise ValidationError(
                    f"У вас уже {MAX_OPEN_PER_TYPE} открытые заявки этого вида. "
                    "Дождитесь их выполнения."
                )
            now = clock.now()
            petition = Petition.objects.create(
                student=student,
                request_type=request_type,
                comment=comment,
                status=SUBMITTED,
                created_at=now,
                status_changed_at=now,
                expected_ready_date=add_working_days(
                    timezone.localdate(now), request_type.processing_days
                ),
            )
            PetitionStatusChange.objects.create(
                petition=petition,
                from_status="",
                to_status=SUBMITTED,
                actor=student.user,
                created_at=now,
            )
            for upload in uploads:
                att = store_attachment(petition, upload, upload.name, upload.size)
                stored.append(att.file.name)
    except BaseException:
        for name in stored:
            get_private_storage().delete(name)
        raise
    return petition


def change_status(
    petition: Petition,
    actor: User,
    expected_status: str,
    new_status: str,
    comment: str = "",
) -> Petition:
    staff = get_profile_for_role(actor, User.Role.STAFF)
    comment = (comment or "").strip()
    if len(comment) > MAX_COMMENT_LENGTH:
        raise ValidationError("Комментарий слишком длинный.")
    with transaction.atomic():
        locked = _lock_petition(petition.pk)
        if locked.student.group.program.faculty_id != staff.faculty_id:
            raise PermissionDenied
        if locked.status != expected_status:
            raise StaleStatusError(StaleStatusError.default_message)
        if not can_transition(locked.status, new_status):
            raise ValidationError(
                f"Нельзя перевести заявку из «{_status_label(locked.status)}» "
                f"в «{_status_label(new_status)}»."
            )
        if new_status in COMMENT_REQUIRED_FOR and not comment:
            raise ValidationError("Укажите причину отклонения.")
        now = clock.now()
        PetitionStatusChange.objects.create(
            petition=locked,
            from_status=locked.status,
            to_status=new_status,
            actor=actor,
            created_at=now,
            comment=comment,
        )
        locked.status = new_status
        locked.status_changed_at = now
        locked.save(update_fields=["status", "status_changed_at"])
    return locked


def add_staff_comment(petition: Petition, actor: User, text: str) -> PetitionComment:
    staff = get_profile_for_role(actor, User.Role.STAFF)
    if petition.student.group.program.faculty_id != staff.faculty_id:
        raise PermissionDenied
    text = (text or "").strip()
    if not text:
        raise ValidationError("Комментарий не может быть пустым.")
    if len(text) > MAX_COMMENT_LENGTH:
        raise ValidationError("Комментарий слишком длинный.")
    return PetitionComment.objects.create(
        petition=petition, author=actor, text=text, created_at=clock.now()
    )
