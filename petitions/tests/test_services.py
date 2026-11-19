from datetime import date
from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from core import clock
from core.storage import get_private_storage
from core.testing import FrozenClockMixin, moscow
from petitions.files import store_attachment
from petitions.models import (
    MAX_COMMENT_LENGTH,
    Petition,
    PetitionAttachment,
    PetitionComment,
    PetitionStatusChange,
)
from petitions.selectors import attachments_visible_to, petitions_visible_to
from petitions.services import (
    StaleStatusError,
    _lock_petition,
    _lock_student,
    add_staff_comment,
    add_working_days,
    change_status,
    submit_petition,
)
from petitions.tests.helpers import fake_upload, make_petition, make_type, pdf_upload


def _drive_to(petition, staff, status):
    path = {
        "submitted": [],
        "in_progress": ["in_progress"],
        "ready": ["in_progress", "ready"],
        "issued": ["in_progress", "ready", "issued"],
        "rejected": ["rejected"],
    }[status]
    for s in path:
        comment = "причина" if s == "rejected" else ""
        change_status(petition, staff, petition.status, s, comment)
        petition.refresh_from_db()
    return petition


class WorkingDaysTests(SimpleTestCase):
    def test_mon_plus_1(self):
        self.assertEqual(add_working_days(date(2026, 11, 16), 1), date(2026, 11, 17))

    def test_fri_plus_1(self):
        self.assertEqual(add_working_days(date(2026, 11, 20), 1), date(2026, 11, 23))

    def test_sat_plus_1(self):
        self.assertEqual(add_working_days(date(2026, 11, 21), 1), date(2026, 11, 23))

    def test_sun_plus_1(self):
        self.assertEqual(add_working_days(date(2026, 11, 22), 1), date(2026, 11, 23))

    def test_fri_plus_5(self):
        self.assertEqual(add_working_days(date(2026, 11, 20), 5), date(2026, 11, 27))

    def test_wed_plus_10(self):
        self.assertEqual(add_working_days(date(2026, 11, 18), 10), date(2026, 12, 2))

    def test_days_less_than_1(self):
        with self.assertRaises(ValueError):
            add_working_days(date(2026, 11, 18), 0)


class SelectorTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac_x = make_faculty("FX")
        self.fac_y = make_faculty("FY")
        self.group_x = make_group(self.fac_x, "GX")
        self.group_y = make_group(self.fac_y, "GY")
        self.student_a = make_student("a", self.group_x, "SA").student_profile
        self.student_b = make_student("b", self.group_y, "SB").student_profile
        self.staff_x = make_staff("sx", self.fac_x)
        self.staff_y = make_staff("sy", self.fac_y)
        self.type = make_type()
        self.pa = make_petition(self.student_a, self.type)
        self.pb = make_petition(self.student_b, self.type)

    def test_student_sees_own_only(self):
        self.assertEqual(set(petitions_visible_to(self.student_a.user)), {self.pa})

    def test_staff_own_faculty(self):
        self.assertEqual(set(petitions_visible_to(self.staff_x)), {self.pa})
        self.assertEqual(set(petitions_visible_to(self.staff_y)), {self.pb})

    def test_superuser_empty(self):
        admin = User.objects.create_superuser(username="admin")
        self.assertFalse(petitions_visible_to(admin).exists())

    def test_anonymous_empty(self):
        self.assertFalse(petitions_visible_to(AnonymousUser()).exists())

    def test_staff_without_profile_empty(self):
        user = User.objects.create_user(username="noprof", role=User.Role.STAFF)
        self.assertFalse(petitions_visible_to(user).exists())

    def test_attachments_follow(self):
        PetitionAttachment.objects.create(
            petition=self.pa, file="request_attachments/aa/a.pdf", original_name="a.pdf", size=1
        )
        self.assertEqual(attachments_visible_to(self.student_a.user).count(), 1)
        self.assertEqual(attachments_visible_to(self.student_b.user).count(), 0)


class SubmitTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.faculty = make_faculty("FDD")
        self.group = make_group(self.faculty, "ЦД-101")
        self.student = make_student("s1", self.group, "ST-0001").student_profile
        self.type = make_type(days=3)

    def test_submit_creates_petition_and_history(self):
        petition = submit_petition(self.student, self.type, "Комментарий", [])
        self.assertEqual(petition.status, "submitted")
        self.assertEqual(petition.expected_ready_date, date(2026, 11, 23))
        self.assertEqual(petition.history.count(), 1)
        row = petition.history.get()
        self.assertEqual(row.from_status, "")
        self.assertEqual(row.to_status, "submitted")
        self.assertEqual(row.actor, self.student.user)

    def test_comment_required_rejected(self):
        req = make_type(name="Справка2", comment_required=True, hint="Причина")
        with self.assertRaises(ValidationError) as cm:
            submit_petition(self.student, req, "", [])
        self.assertTrue(any("комментарий обязателен" in m for m in cm.exception.messages))

    def test_comment_whitespace_only_rejected_when_required(self):
        req = make_type(name="Справка3", comment_required=True, hint="Причина")
        with self.assertRaises(ValidationError):
            submit_petition(self.student, req, "   ", [])

    def test_comment_optional_ok(self):
        petition = submit_petition(self.student, self.type, "", [])
        self.assertEqual(petition.comment, "")

    def test_comment_too_long(self):
        with self.assertRaises(ValidationError):
            submit_petition(self.student, self.type, "x" * (MAX_COMMENT_LENGTH + 1), [])

    def test_inactive_type_rejected(self):
        inactive = make_type(name="Inactive")
        inactive.is_active = False
        inactive.save()
        with self.assertRaises(ValidationError):
            submit_petition(self.student, inactive, "", [])

    def test_attachments_stored_privately(self):
        upload = pdf_upload()
        expected = upload.read()
        upload.seek(0)
        petition = submit_petition(self.student, self.type, "", [upload])
        att = petition.attachments.get()
        self.assertRegex(att.file.name, r"^request_attachments/[0-9a-f]{2}/[0-9a-f]{32}\.pdf$")
        root = str(get_private_storage().location)
        self.assertTrue(att.file.path.startswith(root))
        with att.file.open("rb") as fh:
            self.assertEqual(fh.read(), expected)

    def test_invalid_attachment_rejected_nothing_stored(self):
        bad = fake_upload("evil.exe", b"MZ\x90\x00\x03", "application/octet-stream")
        with self.assertRaises(ValidationError):
            submit_petition(self.student, self.type, "", [bad])
        self.assertEqual(Petition.objects.count(), 0)
        self.assertEqual(PetitionAttachment.objects.count(), 0)

    def test_limit_three_open_per_type(self):
        for _ in range(3):
            submit_petition(self.student, self.type, "", [])
        with self.assertRaises(ValidationError) as cm:
            submit_petition(self.student, self.type, "", [])
        self.assertTrue(any("открытые заявки" in m for m in cm.exception.messages))
        other = make_type(name="Заявление", kind="application", days=5)
        submit_petition(self.student, other, "", [])
        p = Petition.objects.filter(student=self.student, request_type=self.type).first()
        p.status = "issued"
        p.save(update_fields=["status"])
        submit_petition(self.student, self.type, "", [])

    def test_limit_counts_in_progress(self):
        for _ in range(3):
            submit_petition(self.student, self.type, "", [])
        p = Petition.objects.filter(student=self.student, request_type=self.type).first()
        p.status = "in_progress"
        p.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            submit_petition(self.student, self.type, "", [])

    def test_files_removed_on_failure(self):
        saved_names = []
        real_store = store_attachment

        def flaky(petition, upload, original_name, size):
            if saved_names:
                raise RuntimeError("boom")
            att = real_store(petition, upload, original_name, size)
            saved_names.append(att.file.name)
            return att

        uploads = [pdf_upload("a.pdf"), pdf_upload("b.pdf")]
        with mock.patch("petitions.services.store_attachment", side_effect=flaky):
            with self.assertRaises(RuntimeError):
                submit_petition(self.student, self.type, "", uploads)
        self.assertEqual(Petition.objects.count(), 0)
        storage = get_private_storage()
        self.assertFalse(storage.exists(saved_names[0]))

    def test_student_row_locked(self):
        with mock.patch("petitions.services._lock_student", wraps=_lock_student) as patched:
            submit_petition(self.student, self.type, "", [])
        patched.assert_called_once_with(self.student.pk)


class TransitionTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac_x = make_faculty("FX")
        self.fac_y = make_faculty("FY")
        self.group_x = make_group(self.fac_x, "GX")
        self.group_y = make_group(self.fac_y, "GY")
        self.student_a = make_student("a", self.group_x, "SA").student_profile
        self.staff_x = make_staff("sx", self.fac_x)
        self.staff_x2 = make_staff("sx2", self.fac_x)
        self.staff_y = make_staff("sy", self.fac_y)
        self.type = make_type()
        self.petition = make_petition(self.student_a, self.type)

    def test_allowed_transitions(self):
        for from_s, to_s in [
            ("submitted", "in_progress"),
            ("submitted", "rejected"),
            ("in_progress", "ready"),
            ("in_progress", "rejected"),
            ("ready", "issued"),
        ]:
            p = make_petition(self.student_a, self.type)
            _drive_to(p, self.staff_x, from_s)
            change_status(p, self.staff_x, from_s, to_s, comment="c")
            p.refresh_from_db()
            self.assertEqual(p.status, to_s)
            last = p.history.order_by("created_at", "pk").last()
            self.assertEqual(last.from_status, from_s)
            self.assertEqual(last.to_status, to_s)
            self.assertEqual(last.actor, self.staff_x)
            self.assertEqual(last.created_at, timezone.now())
            self.assertEqual(last.comment, "c")

    def test_disallowed_transitions(self):
        disallowed = [
            ("submitted", "ready"),
            ("submitted", "issued"),
            ("submitted", "submitted"),
            ("in_progress", "submitted"),
            ("in_progress", "in_progress"),
            ("in_progress", "issued"),
            ("ready", "submitted"),
            ("ready", "in_progress"),
            ("ready", "ready"),
            ("ready", "rejected"),
            ("issued", "issued"),
            ("issued", "in_progress"),
            ("rejected", "rejected"),
            ("rejected", "submitted"),
        ]
        for from_s, to_s in disallowed:
            p = make_petition(self.student_a, self.type)
            _drive_to(p, self.staff_x, from_s)
            before = p.history.count()
            with self.assertRaises(ValidationError):
                change_status(p, self.staff_x, from_s, to_s)
            p.refresh_from_db()
            self.assertEqual(p.status, from_s)
            self.assertEqual(p.history.count(), before)

    def test_reject_without_comment(self):
        with self.assertRaises(ValidationError) as cm:
            change_status(self.petition, self.staff_x, "submitted", "rejected", "")
        self.assertTrue(any("причину отклонения" in m for m in cm.exception.messages))
        self.petition.refresh_from_db()
        self.assertEqual(self.petition.status, "submitted")

    def test_reject_with_comment(self):
        change_status(self.petition, self.staff_x, "submitted", "rejected", "Причина")
        last = self.petition.history.order_by("created_at", "pk").last()
        self.assertEqual(last.comment, "Причина")
        self.assertEqual(last.to_status, "rejected")

    def test_stale_expected_status_rejected(self):
        change_status(self.petition, self.staff_x, "submitted", "in_progress")
        with self.assertRaises(StaleStatusError) as cm:
            change_status(self.petition, self.staff_x, "submitted", "ready")
        self.assertIn("Заявка уже изменена, обновите страницу.", cm.exception.messages)
        self.petition.refresh_from_db()
        self.assertEqual(self.petition.status, "in_progress")
        self.assertEqual(self.petition.history.count(), 2)

    def test_concurrent_take_and_reject(self):
        change_status(self.petition, self.staff_x, "submitted", "in_progress")
        with self.assertRaises(StaleStatusError):
            change_status(self.petition, self.staff_x2, "submitted", "rejected", "причина")

    def test_student_cannot_transition(self):
        with self.assertRaises(PermissionDenied):
            change_status(self.petition, self.student_a.user, "submitted", "in_progress")

    def test_other_faculty_staff_cannot_transition(self):
        with self.assertRaises(PermissionDenied):
            change_status(self.petition, self.staff_y, "submitted", "in_progress")

    def test_superuser_cannot_transition(self):
        admin = User.objects.create_superuser(username="admin")
        with self.assertRaises(PermissionDenied):
            change_status(self.petition, admin, "submitted", "in_progress")

    def test_lock_used(self):
        with mock.patch("petitions.services._lock_petition", wraps=_lock_petition) as patched:
            change_status(self.petition, self.staff_x, "submitted", "in_progress")
        patched.assert_called_once_with(self.petition.pk)


class CommentTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac_x = make_faculty("FX")
        self.fac_y = make_faculty("FY")
        self.group_x = make_group(self.fac_x, "GX")
        self.group_y = make_group(self.fac_y, "GY")
        self.student_a = make_student("a", self.group_x, "SA").student_profile
        self.staff_x = make_staff("sx", self.fac_x)
        self.staff_x2 = make_staff("sx2", self.fac_x)
        self.staff_y = make_staff("sy", self.fac_y)
        self.type = make_type()
        self.petition = make_petition(self.student_a, self.type)

    def test_append_at_every_status(self):
        for status in ["submitted", "in_progress", "ready", "issued", "rejected"]:
            p = make_petition(self.student_a, self.type)
            _drive_to(p, self.staff_x, status)
            add_staff_comment(p, self.staff_x, "комментарий")
            self.assertEqual(p.staff_comments.count(), 1)

    def test_two_staff_both_add(self):
        c1 = add_staff_comment(self.petition, self.staff_x, "первый")
        add_staff_comment(self.petition, self.staff_x2, "второй")
        self.assertEqual(self.petition.staff_comments.count(), 2)
        c1.refresh_from_db()
        self.assertEqual(c1.text, "первый")
        self.assertEqual(c1.author, self.staff_x)

    def test_empty_rejected(self):
        with self.assertRaises(ValidationError):
            add_staff_comment(self.petition, self.staff_x, "   ")

    def test_student_cannot(self):
        with self.assertRaises(PermissionDenied):
            add_staff_comment(self.petition, self.student_a.user, "x")

    def test_other_faculty_staff_cannot(self):
        with self.assertRaises(PermissionDenied):
            add_staff_comment(self.petition, self.staff_y, "x")

    def test_comment_after_concurrent_transition(self):
        change_status(self.petition, self.staff_x, "submitted", "in_progress")
        comment = add_staff_comment(self.petition, self.staff_x, "заметка")
        self.assertEqual(comment.text, "заметка")


class ServiceClockTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-11 12:00"

    def setUp(self):
        self.faculty = make_faculty("FDD")
        self.group = make_group(self.faculty, "ЦД-101")
        self.student = make_student("s1", self.group, "ST-0001").student_profile
        self.type = make_type(days=3)
        self.staff = make_staff("st1", self.faculty)
        self.now = moscow("2026-11-11 12:00")

    def test_submit_gets_frozen_time(self):
        petition = submit_petition(self.student, self.type, "", [])
        self.assertEqual(petition.created_at, self.now)
        self.assertEqual(petition.status_changed_at, self.now)
        self.assertEqual(petition.history.get().created_at, self.now)

    def test_attachment_gets_frozen_time(self):
        petition = submit_petition(self.student, self.type, "", [pdf_upload()])
        self.assertEqual(petition.attachments.get().uploaded_at, self.now)

    def test_status_change_gets_frozen_time(self):
        petition = submit_petition(self.student, self.type, "", [])
        change_status(petition, self.staff, "submitted", "in_progress")
        petition.refresh_from_db()
        self.assertEqual(petition.status_changed_at, self.now)
        self.assertEqual(petition.history.last().created_at, self.now)

    def test_staff_comment_gets_frozen_time(self):
        petition = submit_petition(self.student, self.type, "", [])
        comment = add_staff_comment(petition, self.staff, "Комментарий")
        self.assertEqual(comment.created_at, self.now)

    def test_model_defaults_are_clock_now(self):
        cases = [
            (Petition, "created_at"),
            (Petition, "status_changed_at"),
            (PetitionStatusChange, "created_at"),
            (PetitionComment, "created_at"),
            (PetitionAttachment, "uploaded_at"),
        ]
        for model, field in cases:
            with self.subTest(model=model.__name__, field=field):
                self.assertIs(model._meta.get_field(field).default, clock.now)


class SubmitSubjectTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.faculty = make_faculty("FDD")
        self.group = make_group(self.faculty, "ЦД-101")
        self.student = make_student("s1", self.group, "ST-0001").student_profile
        self.catch_all = make_type(
            name="Другая справка", days=5, comment_required=True, hint="h", subject_required=True
        )
        self.ordinary = make_type(days=3)

    def test_subject_stored_normalised(self):
        petition = submit_petition(
            self.student, self.catch_all, "коммент", [], subject="  Справка \n о периоде  "
        )
        self.assertEqual(petition.subject, "Справка о периоде")

    def test_subject_required(self):
        for subject in ("", "   "):
            with self.subTest(subject=subject):
                with self.assertRaises(ValidationError) as cm:
                    submit_petition(self.student, self.catch_all, "коммент", [], subject=subject)
                self.assertTrue(
                    any("Укажите, что именно нужно." in m for m in cm.exception.messages)
                )
        self.assertEqual(Petition.objects.count(), 0)

    def test_subject_length(self):
        ok = submit_petition(self.student, self.catch_all, "коммент", [], subject="а" * 150)
        self.assertEqual(len(ok.subject), 150)
        with self.assertRaises(ValidationError) as cm:
            submit_petition(self.student, self.catch_all, "коммент", [], subject="а" * 151)
        self.assertTrue(any("Поле «Тип» слишком длинное." in m for m in cm.exception.messages))

    def test_subject_ignored_without_flag(self):
        petition = submit_petition(self.student, self.ordinary, "", [], subject="X")
        self.assertEqual(petition.subject, "")

    def test_existing_positional_calls_still_work(self):
        petition = submit_petition(self.student, self.ordinary, "", [])
        self.assertEqual(petition.status, "submitted")
