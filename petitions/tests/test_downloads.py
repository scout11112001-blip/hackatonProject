import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, TestCase
from django.urls import get_resolver, reverse
from django.views import static

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from core.testing import FrozenClockMixin
from petitions.files import store_attachment
from petitions.models import PetitionAttachment
from petitions.tests.helpers import make_petition, make_type


class DownloadAccessTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac_x = make_faculty("FX")
        self.fac_y = make_faculty("FY")
        self.group_x = make_group(self.fac_x, "GX")
        self.group_y = make_group(self.fac_y, "GY")
        self.student_a = make_student("a", self.group_x, "SA").student_profile
        self.student_a2 = make_student("a2", self.group_x, "SA2").student_profile
        self.student_b = make_student("b", self.group_y, "SB").student_profile
        self.staff_sx = make_staff("sx", self.fac_x)
        self.staff_sy = make_staff("sy", self.fac_y)
        self.admin = User.objects.create_superuser(username="admin")
        self.type = make_type()
        self.pa, self.fa = self._with_file(self.student_a)
        self.pa2 = make_petition(self.student_a2, self.type)
        self.pb, self.fb = self._with_file(self.student_b)

    def _with_file(self, student, name="a.pdf"):
        petition = make_petition(student, self.type)
        att = store_attachment(petition, ContentFile(b"%PDF-1.4\n%%EOF"), name, 12)
        return petition, att

    def _url(self, petition, att):
        return reverse("petitions:download", args=[petition.public_id, att.public_id])

    def test_anonymous_redirects(self):
        self.client.logout()
        self.assertEqual(self.client.get(self._url(self.pa, self.fa)).status_code, 302)

    def test_student_own_200(self):
        self.client.force_login(self.student_a.user)
        self.assertEqual(self.client.get(self._url(self.pa, self.fa)).status_code, 200)

    def test_other_student_404(self):
        self.client.force_login(self.student_a2.user)
        self.assertEqual(self.client.get(self._url(self.pa, self.fa)).status_code, 404)

    def test_staff_own_faculty_200(self):
        self.client.force_login(self.staff_sx)
        self.assertEqual(self.client.get(self._url(self.pa, self.fa)).status_code, 200)

    def test_other_faculty_staff_404(self):
        self.client.force_login(self.staff_sy)
        self.assertEqual(self.client.get(self._url(self.pa, self.fa)).status_code, 404)

    def test_superuser_404(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self._url(self.pa, self.fa)).status_code, 404)

    def test_mismatched_pair_404(self):
        self.client.force_login(self.student_a.user)
        self.assertEqual(self.client.get(self._url(self.pa, self.fb)).status_code, 404)

    def test_random_uuid_404(self):
        self.client.force_login(self.student_a.user)
        resp = self.client.get(reverse("petitions:download", args=[uuid.uuid4(), uuid.uuid4()]))
        self.assertEqual(resp.status_code, 404)


class DownloadHeadersTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile
        self.type = make_type()
        self.petition = make_petition(self.student, self.type)
        self.content = b"%PDF-1.4\n%%EOF"
        self.att = store_attachment(
            self.petition, ContentFile(self.content), "Справка.pdf", len(self.content)
        )

    def test_download_headers(self):
        self.client.force_login(self.student.user)
        resp = self.client.get(
            reverse("petitions:download", args=[self.petition.public_id, self.att.public_id])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(resp["Content-Disposition"].startswith("attachment;"))
        self.assertIn("filename*=utf-8''", resp["Content-Disposition"])
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertIn("no-store", resp["Cache-Control"])
        self.assertEqual(b"".join(resp.streaming_content), self.content)

    def test_path_traversal_name_not_used(self):
        att = store_attachment(self.petition, ContentFile(b"%PDF-1.4\n%%EOF"), "../../x.pdf", 12)
        self.assertRegex(att.file.name, r"^request_attachments/[0-9a-f]{2}/[0-9a-f]{32}\.pdf$")
        self.assertEqual(att.original_name, "x.pdf")


class StorageSafetyTests(SimpleTestCase):
    def test_no_public_url(self):
        att = PetitionAttachment(file="request_attachments/aa/x.pdf", original_name="x.pdf", size=1)
        with self.assertRaises(ValueError):
            _ = att.file.url

    def test_no_static_serve_patterns(self):
        resolver = get_resolver()

        def walk(patterns):
            for p in patterns:
                if hasattr(p, "url_patterns"):
                    walk(p.url_patterns)
                else:
                    cb = getattr(p.callback, "view_class", p.callback)
                    self.assertIsNot(cb, static.serve)

        walk(resolver.url_patterns)

    def test_private_root_not_in_static(self):
        root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()
        static_root = Path(settings.STATIC_ROOT).resolve()
        self.assertTrue(root != static_root and static_root not in root.parents)
        for d in settings.STATICFILES_DIRS:
            dd = Path(d).resolve()
            self.assertTrue(root != dd and dd not in root.parents)
