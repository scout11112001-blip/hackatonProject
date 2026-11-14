"""Attachment handling: upload path, display name sanitizing, validation, storage."""

import unicodedata
import uuid
from collections.abc import Sequence

from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.db import IntegrityError, transaction

from core.storage import get_private_storage

MAX_ATTACHMENTS = 3
MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024
PDF_CONTENT_TYPE = "application/pdf"
PDF_SIGNATURE = b"%PDF-"
MAX_NAME_ATTEMPTS = 5
ATTACHMENT_DIR = "request_attachments"
MAX_DISPLAY_NAME = 120


class AttachmentStorageError(Exception):
    pass


def attachment_upload_to(instance: object, filename: str) -> str:
    name = uuid.uuid4().hex
    return f"{ATTACHMENT_DIR}/{name[:2]}/{name}.pdf"


def sanitize_display_name(raw: str) -> str:
    name = unicodedata.normalize("NFC", raw or "")
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    kept = [c for c in name if not unicodedata.category(c).startswith("C") and c != '"']
    name = " ".join("".join(kept).split())
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    stem = name[:-4]
    if not stem:
        return "document.pdf"
    if len(name) > MAX_DISPLAY_NAME:
        return stem[: MAX_DISPLAY_NAME - 4] + ".pdf"
    return name


def validate_pdf(upload: UploadedFile) -> None:
    name = sanitize_display_name(upload.name)
    if not upload.name.lower().endswith(".pdf"):
        raise ValidationError(f"Файл «{name}»: допускаются только PDF.")
    if upload.content_type != PDF_CONTENT_TYPE:
        raise ValidationError(f"Файл «{name}»: допускаются только PDF.")
    if upload.size == 0:
        raise ValidationError(f"Файл «{name}» пустой.")
    if upload.size > MAX_ATTACHMENT_SIZE:
        raise ValidationError(f"Файл «{name}» больше 5 МБ.")
    upload.seek(0)
    head = upload.read(5)
    upload.seek(0)
    if head != PDF_SIGNATURE:
        raise ValidationError(f"Файл «{name}» не является PDF.")


def validate_attachments(uploads: Sequence[UploadedFile]) -> None:
    messages: list[str] = []
    if len(uploads) > MAX_ATTACHMENTS:
        messages.append("Можно приложить не больше 3 файлов.")
    for upload in uploads:
        try:
            validate_pdf(upload)
        except ValidationError as exc:
            messages.extend(exc.messages)
    if messages:
        raise ValidationError(messages)


def store_attachment(petition: object, upload: File, original_name: str, size: int) -> "object":
    from petitions.models import PetitionAttachment  # lazy import to avoid a cycle

    storage = get_private_storage()
    for _ in range(MAX_NAME_ATTEMPTS):
        name = attachment_upload_to(None, "")
        if storage.exists(name) or PetitionAttachment.objects.filter(file=name).exists():
            continue
        upload.seek(0)
        try:
            saved = storage.save(name, upload)
        except FileExistsError:
            continue
        if saved != name:
            storage.delete(saved)
            raise RuntimeError("Storage returned an unexpected name.")
        try:
            with transaction.atomic():
                return PetitionAttachment.objects.create(
                    petition=petition,
                    file=saved,
                    original_name=sanitize_display_name(original_name),
                    size=size,
                )
        except IntegrityError:
            storage.delete(saved)
            continue
    raise AttachmentStorageError("Не удалось сохранить файл. Попробуйте ещё раз.")
