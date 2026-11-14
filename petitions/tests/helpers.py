"""Plain helper functions for petition tests."""

from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from petitions.models import (
    Petition,
    PetitionStatusChange,
    RequestType,
)


def pdf_upload(name="doc.pdf", size=None, content_type="application/pdf"):
    if size is None:
        content = b"%PDF-1.4\n%%EOF"
    else:
        content = b"%PDF-1.4\n" + b"0" * (size - len(b"%PDF-1.4\n%%EOF")) + b"%%EOF"
    return SimpleUploadedFile(name, content, content_type=content_type)


def fake_upload(name, content, content_type):
    return SimpleUploadedFile(name, content, content_type=content_type)


def make_type(name="Справка", kind="certificate", days=3, comment_required=False, hint=""):
    return RequestType.objects.create(
        name=name,
        kind=kind,
        processing_days=days,
        comment_required=comment_required,
        comment_hint=hint,
    )


def make_petition(student_profile, request_type, status="submitted", created_at=None):
    ts = created_at or timezone.now()
    petition = Petition.objects.create(
        student=student_profile,
        request_type=request_type,
        status=status,
        created_at=ts,
        status_changed_at=ts,
        expected_ready_date=date(2026, 11, 23),
    )
    PetitionStatusChange.objects.create(
        petition=petition,
        from_status="",
        to_status=status,
        actor=student_profile.user,
        created_at=ts,
    )
    return petition
