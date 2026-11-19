from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_student
from petitions.models import RequestType
from petitions.tests.helpers import make_petition, make_type


class RequestTypeSubjectTests(TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile

    def test_clean_requires_comment(self):
        bad = RequestType(
            name="X",
            kind="certificate",
            processing_days=5,
            subject_required=True,
            comment_required=False,
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()
        good = RequestType(
            name="Y",
            kind="certificate",
            processing_days=5,
            subject_required=True,
            comment_required=True,
            comment_hint="h",
        )
        good.full_clean()

    def test_db_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            RequestType.objects.create(
                name="Z",
                kind="certificate",
                processing_days=5,
                subject_required=True,
                comment_required=False,
            )

    def test_term_label_property(self):
        t = make_type(name="Медленно", days=21)
        self.assertEqual(t.term_label, "до 21 рабочего дня")

    def test_display_name(self):
        t = make_type()
        p = make_petition(self.student, t)
        p.subject = "А"
        self.assertEqual(p.display_name, "Справка: А")
        p.subject = ""
        self.assertEqual(p.display_name, "Справка")

    def test_admin_shows_flag(self):
        make_type()
        User.objects.create_superuser(username="admin", password="Super-Pass-2026!")
        self.client.force_login(User.objects.get(username="admin"))
        resp = self.client.get(reverse("admin:petitions_requesttype_changelist"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Нужно поле «Тип»", resp.content.decode())
        add_resp = self.client.get(reverse("admin:petitions_requesttype_add"))
        self.assertIn('name="subject_required"', add_resp.content.decode())
