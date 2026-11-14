import uuid
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase

from accounts.tests.helpers import make_faculty, make_group, make_student
from core.storage import get_private_storage
from core.testing import FrozenClockMixin
from petitions.files import (
    AttachmentStorageError,
    attachment_upload_to,
    sanitize_display_name,
    store_attachment,
    validate_attachments,
    validate_pdf,
)
from petitions.models import PetitionAttachment
from petitions.tests.helpers import fake_upload, make_petition, make_type, pdf_upload


class UploadToTests(SimpleTestCase):
    def test_upload_to_format(self):
        path = attachment_upload_to(None, "../../evil.exe")
        self.assertRegex(path, r"^request_attachments/[0-9a-f]{2}/[0-9a-f]{32}\.pdf$")
        name = path.split("/")[-1][:-4]
        self.assertEqual(path.split("/")[1], name[:2])

    def test_upload_to_uses_uuid4(self):
        u = uuid.UUID(int=1)
        with mock.patch("petitions.files.uuid.uuid4", return_value=u):
            path = attachment_upload_to(None, "../../evil.exe")
        self.assertEqual(path, f"request_attachments/{u.hex[:2]}/{u.hex}.pdf")


class SanitizeTests(SimpleTestCase):
    def test_path_traversal(self):
        self.assertEqual(sanitize_display_name("../../etc/passwd.pdf"), "passwd.pdf")

    def test_windows_path(self):
        self.assertEqual(sanitize_display_name("C:\\x\\Справка.PDF"), "Справка.PDF")

    def test_control_chars_removed(self):
        self.assertEqual(sanitize_display_name("a\x00b\x1f.pdf"), "ab.pdf")

    def test_long_name_truncated(self):
        result = sanitize_display_name("x" * 300 + ".pdf")
        self.assertEqual(len(result), 120)
        self.assertTrue(result.endswith(".pdf"))

    def test_empty(self):
        self.assertEqual(sanitize_display_name(""), "document.pdf")


class ValidatePdfTests(SimpleTestCase):
    def test_valid(self):
        validate_pdf(pdf_upload())

    def test_uppercase_pdf_ok(self):
        validate_pdf(fake_upload("doc.PDF", b"%PDF-1.4\n", "application/pdf"))

    def test_wrong_extension(self):
        upload = fake_upload("doc.txt", b"%PDF-1.4\n", "application/pdf")
        with self.assertRaises(ValidationError):
            validate_pdf(upload)

    def test_wrong_content_type(self):
        upload = fake_upload("doc.pdf", b"%PDF-1.4\n", "text/plain")
        with self.assertRaises(ValidationError):
            validate_pdf(upload)

    def test_renamed_non_pdf(self):
        upload = fake_upload("doc.pdf", b"MZ\x90\x00\x03", "application/pdf")
        with self.assertRaises(ValidationError):
            validate_pdf(upload)

    def test_empty(self):
        upload = fake_upload("doc.pdf", b"", "application/pdf")
        with self.assertRaises(ValidationError):
            validate_pdf(upload)

    def test_5mb_exactly_ok(self):
        upload = SimpleUploadedFile(
            "doc.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024 - 5), content_type="application/pdf"
        )
        validate_pdf(upload)

    def test_5mb_plus_1_rejected(self):
        upload = SimpleUploadedFile(
            "doc.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024 - 4), content_type="application/pdf"
        )
        with self.assertRaises(ValidationError):
            validate_pdf(upload)


class ValidateAttachmentsTests(SimpleTestCase):
    def test_three_ok(self):
        validate_attachments([pdf_upload(f"d{i}.pdf") for i in range(3)])

    def test_four_rejected(self):
        uploads = [pdf_upload(f"d{i}.pdf") for i in range(4)]
        with self.assertRaises(ValidationError) as cm:
            validate_attachments(uploads)
        self.assertTrue(any("не больше 3 файлов" in m for m in cm.exception.messages))

    def test_multiple_bad_files_all_reported(self):
        uploads = [
            fake_upload("a.txt", b"%PDF", "application/pdf"),
            fake_upload("b.pdf", b"nope", "text/plain"),
        ]
        with self.assertRaises(ValidationError) as cm:
            validate_attachments(uploads)
        self.assertGreaterEqual(len(cm.exception.messages), 2)


class StoreAttachmentTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.faculty = make_faculty("FDD")
        self.group = make_group(self.faculty, "ЦД-101")
        student_user = make_student("s1", self.group, "ST-0001")
        self.student = student_user.student_profile
        self.type = make_type()
        self.petition = make_petition(self.student, self.type)

    def test_store_retries_on_existing_file(self):
        storage = get_private_storage()
        u1 = uuid.UUID(int=100)
        u2 = uuid.UUID(int=101)
        name1 = f"request_attachments/{u1.hex[:2]}/{u1.hex}.pdf"
        storage.save(name1, ContentFile(b"existing"))
        upload = ContentFile(b"%PDF-data")
        with mock.patch("petitions.files.uuid.uuid4", side_effect=[u1, u1, u2]):
            att = store_attachment(self.petition, upload, "doc.pdf", upload.size)
        name2 = f"request_attachments/{u2.hex[:2]}/{u2.hex}.pdf"
        self.assertEqual(att.file.name, name2)
        with storage.open(name1, "rb") as fh:
            self.assertEqual(fh.read(), b"existing")

    def test_store_retries_on_db_collision(self):
        u1 = uuid.UUID(int=200)
        u2 = uuid.UUID(int=201)
        name1 = f"request_attachments/{u1.hex[:2]}/{u1.hex}.pdf"
        PetitionAttachment.objects.create(
            petition=self.petition, file=name1, original_name="x.pdf", size=1
        )
        upload = ContentFile(b"%PDF-data")
        with mock.patch("petitions.files.uuid.uuid4", side_effect=[u1, u2]):
            att = store_attachment(self.petition, upload, "doc.pdf", upload.size)
        name2 = f"request_attachments/{u2.hex[:2]}/{u2.hex}.pdf"
        self.assertEqual(att.file.name, name2)

    def test_store_gives_up(self):
        storage = get_private_storage()
        u1 = uuid.UUID(int=300)
        name1 = f"request_attachments/{u1.hex[:2]}/{u1.hex}.pdf"
        storage.save(name1, ContentFile(b"existing"))
        upload = ContentFile(b"%PDF-data")
        with mock.patch("petitions.files.uuid.uuid4", return_value=u1):
            with self.assertRaises(AttachmentStorageError):
                store_attachment(self.petition, upload, "doc.pdf", upload.size)
        self.assertEqual(PetitionAttachment.objects.filter(petition=self.petition).count(), 0)

    def test_db_unique_path(self):
        PetitionAttachment.objects.create(
            petition=self.petition,
            file="request_attachments/aa/dup.pdf",
            original_name="a.pdf",
            size=1,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PetitionAttachment.objects.create(
                    petition=self.petition,
                    file="request_attachments/aa/dup.pdf",
                    original_name="b.pdf",
                    size=1,
                )
