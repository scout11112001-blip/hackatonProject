"""Model and constraint tests for the chat app."""

import uuid

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import StaffProfile
from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from chat.models import AuthorRole, Dialog, Message
from chat.tests.helpers import add_message, make_dialog


class ModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.student = make_student("stu", cls.group, "REC-1")
        cls.other_student = make_student("stu2", cls.group, "REC-2")
        cls.staff = make_staff("stf", cls.faculty)
        cls.profile = cls.student.student_profile
        cls.other_profile = cls.other_student.student_profile

    def test_one_dialog_per_student(self):
        make_dialog(self.profile)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Dialog.objects.create(student=self.profile)

    def test_db_rejects_empty_text(self):
        dialog = make_dialog(self.profile)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Message.objects.create(
                    dialog=dialog,
                    author=self.student,
                    author_role=AuthorRole.STUDENT,
                    text="",
                )

    def test_db_rejects_bad_role(self):
        dialog = make_dialog(self.profile)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Message.objects.create(
                    dialog=dialog, author=self.student, author_role="bad", text="x"
                )

    def test_client_token_unique_per_dialog(self):
        dialog = make_dialog(self.profile)
        other = make_dialog(self.other_profile)
        token = uuid.uuid4()
        Message.objects.create(
            dialog=dialog,
            author=self.student,
            author_role=AuthorRole.STUDENT,
            text="x",
            client_token=token,
        )
        # Same token in the same dialog is rejected.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Message.objects.create(
                    dialog=dialog,
                    author=self.student,
                    author_role=AuthorRole.STUDENT,
                    text="y",
                    client_token=token,
                )
        # The same token in another dialog is fine.
        Message.objects.create(
            dialog=other,
            author=self.other_student,
            author_role=AuthorRole.STUDENT,
            text="z",
            client_token=token,
        )
        # Many NULL tokens are fine.
        add_message(dialog, self.student, AuthorRole.STUDENT)
        add_message(dialog, self.student, AuthorRole.STUDENT)
        self.assertEqual(Message.objects.filter(dialog=dialog).count(), 3)

    def test_ordering_by_id(self):
        dialog = make_dialog(self.profile)
        a = add_message(dialog, self.student, AuthorRole.STUDENT)
        b = add_message(dialog, self.staff, AuthorRole.STAFF)
        c = add_message(dialog, self.student, AuthorRole.STUDENT)
        self.assertEqual(list(Message.objects.values_list("id", flat=True)), [a.pk, b.pk, c.pk])

    def test_staff_short_name_nbsp(self):
        profile = StaffProfile.objects.get(user=self.staff)
        profile.middle_name = "Петрович"
        profile.save(update_fields=["middle_name"])
        self.assertEqual(profile.short_name, "stf-last\u00a0s.\u00a0П.")
        profile.middle_name = ""
        profile.save(update_fields=["middle_name"])
        self.assertEqual(profile.short_name, "stf-last\u00a0s.")
