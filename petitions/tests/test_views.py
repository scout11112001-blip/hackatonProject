import re
import uuid
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from core.testing import FrozenClockMixin
from petitions.files import store_attachment
from petitions.forms import PetitionForm
from petitions.models import Petition, PetitionComment, PetitionStatusChange
from petitions.services import add_staff_comment, change_status
from petitions.tests.helpers import fake_upload, make_petition, make_type, pdf_upload


class AccessMatrixTests(FrozenClockMixin, TestCase):
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
        self.inactive = make_type(name="Inactive")
        self.inactive.is_active = False
        self.inactive.save()
        self.pa = make_petition(self.student_a, self.type)
        self.pa2 = make_petition(self.student_a2, self.type)
        self.pb = make_petition(self.student_b, self.type)

    def _login(self, user):
        self.client.force_login(user)

    def test_my_list_access(self):
        self.assertEqual(self.client.get(reverse("petitions:my_list")).status_code, 302)
        self._login(self.student_a.user)
        resp = self.client.get(reverse("petitions:my_list"))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn(str(self.pa.short_id), content)
        self.assertNotIn(str(self.pa2.short_id), content)
        self.assertNotIn(str(self.pb.short_id), content)
        self._login(self.staff_sx)
        self.assertEqual(self.client.get(reverse("petitions:my_list")).status_code, 403)

    def test_catalog_access(self):
        self.assertEqual(self.client.get(reverse("petitions:catalog")).status_code, 302)
        self._login(self.student_a.user)
        self.assertEqual(self.client.get(reverse("petitions:catalog")).status_code, 200)
        self._login(self.staff_sx)
        self.assertEqual(self.client.get(reverse("petitions:catalog")).status_code, 403)
        self._login(self.admin)
        self.assertEqual(self.client.get(reverse("petitions:catalog")).status_code, 403)

    def test_submit_access(self):
        url = reverse("petitions:submit", args=[self.type.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self._login(self.student_a.user)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {"comment": "x"}).status_code, 302)
        self._login(self.staff_sx)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_inactive_type_404(self):
        self._login(self.student_a.user)
        url = reverse("petitions:submit", args=[self.inactive.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_detail_other_student_404(self):
        self._login(self.student_a2.user)
        self.assertEqual(self.client.get(self._detail(self.pa.public_id)).status_code, 404)

    def test_detail_staff_403(self):
        self._login(self.staff_sx)
        self.assertEqual(self.client.get(self._detail(self.pa.public_id)).status_code, 403)

    def test_submitted_page_other_student_404(self):
        self._login(self.student_a2.user)
        self.assertEqual(self.client.get(self._submitted(self.pa)).status_code, 404)

    def test_staff_queue_own_faculty_only(self):
        self.assertEqual(self.client.get(reverse("petitions:staff_queue")).status_code, 302)
        self._login(self.student_a.user)
        self.assertEqual(self.client.get(reverse("petitions:staff_queue")).status_code, 403)
        self._login(self.staff_sx)
        content = self.client.get(reverse("petitions:staff_queue")).content.decode()
        self.assertIn(str(self.pa.short_id), content)
        self.assertIn(str(self.pa2.short_id), content)
        self.assertNotIn(str(self.pb.short_id), content)
        self._login(self.staff_sy)
        content = self.client.get(reverse("petitions:staff_queue")).content.decode()
        self.assertIn(str(self.pb.short_id), content)
        self.assertNotIn(str(self.pa.short_id), content)
        self._login(self.admin)
        self.assertEqual(self.client.get(reverse("petitions:staff_queue")).status_code, 403)

    def test_staff_detail_other_faculty_404(self):
        self._login(self.staff_sx)
        self.assertEqual(self.client.get(self._staff_detail(self.pa)).status_code, 200)
        self._login(self.staff_sy)
        self.assertEqual(self.client.get(self._staff_detail(self.pa)).status_code, 404)

    def test_staff_transition_other_faculty_404(self):
        self._login(self.staff_sy)
        resp = self.client.post(
            self._transition(self.pa),
            {"expected_status": "submitted", "new_status": "in_progress"},
        )
        self.assertEqual(resp.status_code, 404)
        self.pa.refresh_from_db()
        self.assertEqual(self.pa.status, "submitted")

    def test_staff_transition_get_405(self):
        self._login(self.staff_sx)
        self.assertEqual(self.client.get(self._transition(self.pa)).status_code, 405)

    def test_staff_comment_other_faculty_404(self):
        self._login(self.staff_sy)
        resp = self.client.post(self._comment(self.pa), {"text": "hello"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(self.pa.staff_comments.count(), 0)

    def test_random_uuid_404(self):
        self._login(self.student_a.user)
        self.assertEqual(self.client.get(self._detail(uuid.uuid4())).status_code, 404)

    def test_sequential_ids_not_used(self):
        url = reverse("petitions:detail", args=[self.pa.public_id])
        self.assertIn(str(self.pa.public_id), url)
        segment = url.rstrip("/").split("/")[-1]
        self.assertNotEqual(segment, str(self.pa.pk))

    def _detail(self, arg):
        return reverse("petitions:detail", args=[arg])

    def _submitted(self, petition):
        return reverse("petitions:submitted", args=[petition.public_id])

    def _staff_detail(self, petition):
        return reverse("petitions:staff_detail", args=[petition.public_id])

    def _transition(self, petition):
        return reverse("petitions:staff_transition", args=[petition.public_id])

    def _comment(self, petition):
        return reverse("petitions:staff_comment", args=[petition.public_id])


class FormTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile
        self.type = make_type()
        self.req_type = make_type(name="Req", comment_required=True, hint="Укажите причину")
        self.url = reverse("petitions:submit", args=[self.type.pk])
        self.req_url = reverse("petitions:submit", args=[self.req_type.pk])

    def test_form_has_exactly_two_fields(self):
        form = PetitionForm(request_type=self.type)
        self.assertEqual(list(form.fields.keys()), ["comment", "files"])

    def test_hint_shown_for_required_comment(self):
        self.client.force_login(self.student.user)
        resp = self.client.get(self.req_url)
        self.assertIn("Укажите причину", resp.content.decode())

    def test_hint_rendered_once(self):
        hint = "Обязательно укажите причину обращения."
        t = make_type(name="H1", comment_required=True, hint=hint)
        self.client.force_login(self.student.user)
        resp = self.client.get(reverse("petitions:submit", args=[t.pk]))
        self.assertEqual(resp.content.decode().count(hint), 1)

    def test_no_hint_for_optional_type(self):
        hint = "Можно указать, куда нужна справка."
        t = make_type(name="H2", comment_required=False, hint=hint)
        self.client.force_login(self.student.user)
        resp = self.client.get(reverse("petitions:submit", args=[t.pk]))
        content = resp.content.decode()
        self.assertLessEqual(content.count(hint), 1)
        self.assertNotIn('class="hint"', content)

    def test_required_comment_missing_shows_error(self):
        self.client.force_login(self.student.user)
        resp = self.client.post(self.req_url, {"comment": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("errorlist", resp.content.decode())
        self.assertEqual(Petition.objects.count(), 0)

    def test_optional_comment_submit(self):
        self.client.force_login(self.student.user)
        resp = self.client.post(self.url, {"comment": ""})
        self.assertEqual(resp.status_code, 302)
        petition = Petition.objects.get()
        self.assertEqual(
            resp["Location"], reverse("petitions:submitted", args=[petition.public_id])
        )

    def test_upload_valid_pdfs(self):
        self.client.force_login(self.student.user)
        resp = self.client.post(
            self.url, {"comment": "", "files": [pdf_upload("a.pdf"), pdf_upload("b.pdf")]}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Petition.objects.get().attachments.count(), 2)

    def test_upload_four_files_rejected(self):
        self.client.force_login(self.student.user)
        files = [pdf_upload(f"f{i}.pdf") for i in range(4)]
        resp = self.client.post(self.url, {"comment": "", "files": files})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("не больше 3 файлов", resp.content.decode())
        self.assertEqual(Petition.objects.count(), 0)

    def test_upload_non_pdf_rejected(self):
        self.client.force_login(self.student.user)
        bad = fake_upload("evil.pdf", b"MZ\x90\x00\x03", "application/pdf")
        resp = self.client.post(self.url, {"comment": "", "files": [bad]})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("не является PDF", resp.content.decode())

    def test_upload_wrong_content_type_rejected(self):
        self.client.force_login(self.student.user)
        bad = fake_upload("a.pdf", b"%PDF-1.4\n", "text/plain")
        resp = self.client.post(self.url, {"comment": "", "files": [bad]})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("только PDF", resp.content.decode())

    def test_upload_too_large_rejected(self):
        self.client.force_login(self.student.user)
        big = SimpleUploadedFile(
            "big.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024 - 4), content_type="application/pdf"
        )
        resp = self.client.post(self.url, {"comment": "", "files": [big]})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("больше 5 МБ", resp.content.decode())

    def test_limit_message_shown(self):
        self.client.force_login(self.student.user)
        for _ in range(3):
            self.client.post(self.url, {"comment": ""})
        resp = self.client.post(self.url, {"comment": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("открытые заявки", resp.content.decode())

    def test_csrf_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student.user)
        resp = client.post(self.url, {"comment": "x"})
        self.assertEqual(resp.status_code, 403)


class StudentPagesTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile
        self.staff = make_staff("sx", self.fac)
        self.cert = make_type(name="Справка об обучении", kind="certificate", days=3)
        self.appl = make_type(name="Заявление", kind="application", days=10)
        self.petition = make_petition(self.student, self.cert)

    def test_catalog_lists_active_types_by_kind(self):
        self.client.force_login(self.student.user)
        resp = self.client.get(reverse("petitions:catalog"))
        content = resp.content.decode()
        self.assertIn("Справки", content)
        self.assertIn("Заявления", content)
        self.assertIn("Справка об обучении", content)
        self.assertIn("Заявление", content)

    def test_my_list_newest_first_and_status_text(self):
        older = make_petition(
            self.student, self.cert, created_at=timezone.now() - timedelta(days=1)
        )
        self.client.force_login(self.student.user)
        content = self.client.get(reverse("petitions:my_list")).content.decode()
        self.assertIn("Подана", content)
        self.assertLess(
            content.index(str(self.petition.short_id)), content.index(str(older.short_id))
        )

    def test_my_list_empty_state(self):
        self.petition.delete()
        self.client.force_login(self.student.user)
        resp = self.client.get(reverse("petitions:my_list"))
        self.assertIn("Заявок пока нет", resp.content.decode())

    def test_catalog_link_on_list_with_requests(self):
        self.client.force_login(self.student.user)
        resp = self.client.get(reverse("petitions:my_list"))
        content = resp.content.decode()
        self.assertEqual(content.count('href="/requests/new/"'), 1)
        self.assertIn("Подать заявку", content)

    def test_catalog_link_on_empty_list(self):
        self.petition.delete()
        self.client.force_login(self.student.user)
        resp = self.client.get(reverse("petitions:my_list"))
        content = resp.content.decode()
        self.assertEqual(content.count('href="/requests/new/"'), 1)
        self.assertIn("Заявок пока нет.", content)

    def test_detail_shows_history_comments_attachments(self):
        store_attachment(self.petition, ContentFile(b"%PDF-1.4\n%%EOF"), "a.pdf", 12)
        add_staff_comment(self.petition, self.staff, "текст комментария")
        self.client.force_login(self.student.user)
        resp = self.client.get(reverse("petitions:detail", args=[self.petition.public_id]))
        content = resp.content.decode()
        self.assertIn("a.pdf", content)
        self.assertIn("текст комментария", content)
        self.assertIn("Подана", content)

    def test_detail_has_no_action_forms(self):
        self.client.force_login(self.student.user)
        resp = self.client.get(reverse("petitions:detail", args=[self.petition.public_id]))
        content = resp.content.decode()
        self.assertNotIn("Отозвать", content)
        self.assertNotIn("staff_transition", content)

    def test_submitted_page_shows_expected_date(self):
        self.client.force_login(self.student.user)
        resp = self.client.get(reverse("petitions:submitted", args=[self.petition.public_id]))
        self.assertIn("Ожидаемая дата готовности", resp.content.decode())


class StaffPagesTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile
        self.staff = make_staff("sx", self.fac)
        self.type = make_type()
        self.p_old = make_petition(
            self.student, self.type, created_at=timezone.now() - timedelta(days=2)
        )
        self.p_new = make_petition(
            self.student, self.type, created_at=timezone.now() - timedelta(days=1)
        )

    def test_queue_default_open_oldest_first(self):
        self.client.force_login(self.staff)
        content = self.client.get(reverse("petitions:staff_queue")).content.decode()
        self.assertLess(
            content.index(str(self.p_old.short_id)), content.index(str(self.p_new.short_id))
        )

    def test_queue_filter_status(self):
        issued = make_petition(self.student, self.type, status="issued")
        self.client.force_login(self.staff)
        content = self.client.get(
            reverse("petitions:staff_queue"), {"status": "issued"}
        ).content.decode()
        self.assertIn(str(issued.short_id), content)
        self.assertNotIn(str(self.p_old.short_id), content)

    def test_queue_filter_all(self):
        issued = make_petition(self.student, self.type, status="issued")
        self.client.force_login(self.staff)
        content = self.client.get(
            reverse("petitions:staff_queue"), {"status": "all"}
        ).content.decode()
        self.assertIn(str(issued.short_id), content)
        self.assertIn(str(self.p_old.short_id), content)

    def test_queue_filter_type(self):
        other = make_type(name="Заявление", kind="application", days=5)
        p_other = make_petition(self.student, other)
        self.client.force_login(self.staff)
        content = self.client.get(
            reverse("petitions:staff_queue"), {"type": str(other.pk)}
        ).content.decode()
        self.assertIn(str(p_other.short_id), content)
        self.assertNotIn(str(self.p_old.short_id), content)

    def test_queue_invalid_filter_falls_back(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("petitions:staff_queue"), {"status": "bogus"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(str(self.p_old.short_id), resp.content.decode())

    def test_queue_empty_state(self):
        Petition.objects.all().delete()
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("petitions:staff_queue"))
        self.assertIn("Заявок нет", resp.content.decode())

    def test_detail_shows_student_info_and_actions(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("petitions:staff_detail", args=[self.p_old.public_id]))
        content = resp.content.decode()
        self.assertIn(self.student.full_name, content)
        self.assertIn(f"<p>{self.student.group.name}</p>", content)
        self.assertIn("Взять в работу", content)
        self.assertIn("Отклонить", content)

    def test_final_status_has_no_actions(self):
        issued = make_petition(self.student, self.type, status="issued")
        self.client.force_login(self.staff)
        content = self.client.get(
            reverse("petitions:staff_detail", args=[issued.public_id])
        ).content.decode()
        self.assertNotIn("Взять в работу", content)
        self.assertNotIn("Отметить готовой", content)
        self.assertNotIn("Отметить выданной", content)
        self.assertNotIn("Отклонить", content)


class StaffActionTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile
        self.staff = make_staff("sx", self.fac)
        self.type = make_type()
        self.petition = make_petition(self.student, self.type)
        self.transition_url = reverse("petitions:staff_transition", args=[self.petition.public_id])
        self.comment_url = reverse("petitions:staff_comment", args=[self.petition.public_id])

    def test_take_ready_issue_flow(self):
        self.client.force_login(self.staff)
        self.client.post(
            self.transition_url, {"expected_status": "submitted", "new_status": "in_progress"}
        )
        self.client.post(
            self.transition_url, {"expected_status": "in_progress", "new_status": "ready"}
        )
        resp = self.client.post(
            self.transition_url, {"expected_status": "ready", "new_status": "issued"}, follow=True
        )
        self.petition.refresh_from_db()
        self.assertEqual(self.petition.status, "issued")
        self.assertEqual(self.petition.history.count(), 4)
        self.assertIn("Статус изменён", resp.content.decode())

    def test_reject_requires_comment(self):
        self.client.force_login(self.staff)
        resp = self.client.post(
            self.transition_url,
            {"expected_status": "submitted", "new_status": "rejected"},
            follow=True,
        )
        self.assertIn("причину отклонения", resp.content.decode())
        self.petition.refresh_from_db()
        self.assertEqual(self.petition.status, "submitted")

    def test_reject_with_comment(self):
        self.client.force_login(self.staff)
        self.client.post(
            self.transition_url,
            {"expected_status": "submitted", "new_status": "rejected", "comment": "причина"},
        )
        self.petition.refresh_from_db()
        self.assertEqual(self.petition.status, "rejected")
        self.assertEqual(
            self.petition.history.order_by("created_at", "pk").last().comment, "причина"
        )

    def test_invalid_transition_message(self):
        self.client.force_login(self.staff)
        resp = self.client.post(
            self.transition_url,
            {"expected_status": "submitted", "new_status": "issued"},
            follow=True,
        )
        self.assertIn("Нельзя перевести заявку", resp.content.decode())
        self.petition.refresh_from_db()
        self.assertEqual(self.petition.status, "submitted")

    def test_stale_message_shown(self):
        change_status(self.petition, self.staff, "submitted", "in_progress")
        self.client.force_login(self.staff)
        resp = self.client.post(
            self.transition_url,
            {"expected_status": "submitted", "new_status": "ready"},
            follow=True,
        )
        self.assertIn("Заявка уже изменена, обновите страницу", resp.content.decode())
        self.petition.refresh_from_db()
        self.assertEqual(self.petition.status, "in_progress")

    def test_comment_added_and_visible_to_student(self):
        self.client.force_login(self.staff)
        self.client.post(self.comment_url, {"text": "проверьте документы"})
        self.assertEqual(self.petition.staff_comments.count(), 1)
        self.client.force_login(self.student.user)
        resp = self.client.get(reverse("petitions:detail", args=[self.petition.public_id]))
        self.assertIn("проверьте документы", resp.content.decode())

    def test_empty_comment_rejected(self):
        self.client.force_login(self.staff)
        self.client.post(self.comment_url, {"text": "  "})
        self.assertEqual(self.petition.staff_comments.count(), 0)

    def test_tampered_form_values(self):
        self.client.force_login(self.staff)
        resp = self.client.post(
            self.transition_url,
            {"expected_status": "submitted", "new_status": "unknown"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.petition.refresh_from_db()
        self.assertEqual(self.petition.status, "submitted")


class NavigationTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile
        self.staff = make_staff("sx", self.fac)
        self.admin = User.objects.create_superuser(username="admin")

    def test_student_nav(self):
        self.client.force_login(self.student.user)
        content = self.client.get(reverse("core:home")).content.decode()
        self.assertIn("/requests/", content)

    def test_staff_nav(self):
        self.client.force_login(self.staff)
        content = self.client.get(reverse("core:home")).content.decode()
        self.assertIn("/staff/requests/", content)

    def test_superuser_neither(self):
        self.client.force_login(self.admin)
        content = self.client.get(reverse("core:home")).content.decode()
        self.assertNotIn("/requests/", content)
        self.assertNotIn("/staff/requests/", content)


class QueryCountTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile
        self.staff = make_staff("sx", self.fac)
        self.type = make_type()
        self.petition = make_petition(self.student, self.type)
        add_staff_comment(self.petition, self.staff, "текст")
        store_attachment(self.petition, ContentFile(b"%PDF-1.4\n%%EOF"), "a.pdf", 12)

    def _num_queries(self, url):
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(url)
        return len(ctx)

    def test_my_list_constant_queries(self):
        self.client.force_login(self.student.user)
        url = reverse("petitions:my_list")
        n1 = self._num_queries(url)
        for _ in range(5):
            make_petition(self.student, self.type)
        self.assertEqual(self._num_queries(url), n1)

    def test_staff_queue_constant_queries(self):
        self.client.force_login(self.staff)
        url = reverse("petitions:staff_queue")
        n1 = self._num_queries(url)
        for _ in range(5):
            make_petition(self.student, self.type)
        self.assertEqual(self._num_queries(url), n1)

    def test_student_detail_constant_queries(self):
        self.client.force_login(self.student.user)
        url = reverse("petitions:detail", args=[self.petition.public_id])
        n1 = self._num_queries(url)
        for _ in range(10):
            PetitionStatusChange.objects.create(
                petition=self.petition,
                from_status="submitted",
                to_status="in_progress",
                actor=self.staff,
                created_at=timezone.now(),
            )
        for i in range(5):
            PetitionComment.objects.create(petition=self.petition, author=self.staff, text=f"c{i}")
        for i in range(5):
            store_attachment(self.petition, ContentFile(b"%PDF-1.4\n%%EOF"), f"f{i}.pdf", 12)
        self.assertEqual(self._num_queries(url), n1)

    def test_staff_detail_constant_queries(self):
        self.client.force_login(self.staff)
        url = reverse("petitions:staff_detail", args=[self.petition.public_id])
        n1 = self._num_queries(url)
        for _ in range(10):
            PetitionStatusChange.objects.create(
                petition=self.petition,
                from_status="submitted",
                to_status="in_progress",
                actor=self.staff,
                created_at=timezone.now(),
            )
        for i in range(5):
            PetitionComment.objects.create(petition=self.petition, author=self.staff, text=f"c{i}")
        for i in range(5):
            store_attachment(self.petition, ContentFile(b"%PDF-1.4\n%%EOF"), f"f{i}.pdf", 12)
        self.assertEqual(self._num_queries(url), n1)

    def test_lists_constant_with_subject(self):
        catch_all = make_type(
            name="Другая справка", days=5, comment_required=True, hint="h", subject_required=True
        )
        self.client.force_login(self.student.user)
        url = reverse("petitions:my_list")
        n1 = self._num_queries(url)
        for _ in range(5):
            p = make_petition(self.student, catch_all)
            p.subject = "Справка о периоде"
            p.save(update_fields=["subject"])
        self.assertEqual(self._num_queries(url), n1)

        self.client.force_login(self.staff)
        url2 = reverse("petitions:staff_queue")
        n2 = self._num_queries(url2)
        for _ in range(5):
            p = make_petition(self.student, catch_all)
            p.subject = "Справка о периоде"
            p.save(update_fields=["subject"])
        self.assertEqual(self._num_queries(url2), n2)


class SubjectFormTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile
        self.catch_all = make_type(
            name="Другая справка",
            days=5,
            comment_required=True,
            hint="Опишите, что нужно и для чего.",
            subject_required=True,
        )
        self.military = make_type(
            name="Справка в военкомат", comment_required=True, hint="Укажите военкомат."
        )
        self.ordinary = make_type()
        self.client.force_login(self.student.user)

    def test_field_shown_only_with_flag(self):
        catch_url = reverse("petitions:submit", args=[self.catch_all.pk])
        content = self.client.get(catch_url).content.decode()
        self.assertIn('name="subject"', content)
        self.assertIn('maxlength="150"', content)
        self.assertIn("Тип", content)
        self.assertLess(content.index('name="subject"'), content.index('name="comment"'))

        for t in (self.ordinary, self.military):
            url = reverse("petitions:submit", args=[t.pk])
            content = self.client.get(url).content.decode()
            self.assertNotIn('name="subject"', content)

    def test_subject_required_errors(self):
        url = reverse("petitions:submit", args=[self.catch_all.pk])
        for subject in ("", "   "):
            with self.subTest(subject=subject):
                resp = self.client.post(url, {"subject": subject, "comment": "к"})
                self.assertEqual(resp.status_code, 200)
                self.assertIn("Укажите, что именно нужно.", resp.content.decode())
                self.assertEqual(Petition.objects.count(), 0)
        with self.subTest(subject="151"):
            resp = self.client.post(url, {"subject": "а" * 151, "comment": "к"})
            self.assertEqual(resp.status_code, 200)
            self.assertIn("errorlist", resp.content.decode())
            self.assertEqual(Petition.objects.count(), 0)

    def test_subject_150_ok_and_normalised(self):
        url = reverse("petitions:submit", args=[self.catch_all.pk])
        resp = self.client.post(url, {"subject": "  " + "а" * 150 + "  ", "comment": "к"})
        self.assertEqual(resp.status_code, 302)
        petition = Petition.objects.get()
        self.assertEqual(len(petition.subject), 150)
        self.assertEqual(petition.subject, "а" * 150)
        self.assertIn("submitted", resp["Location"])

    def test_comment_required_for_catch_all(self):
        url = reverse("petitions:submit", args=[self.catch_all.pk])
        resp = self.client.post(url, {"subject": "Справка о периоде обучения", "comment": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Обязательное поле.", resp.content.decode())
        self.assertEqual(Petition.objects.count(), 0)

    def test_military_comment_required(self):
        url = reverse("petitions:submit", args=[self.military.pk])
        get_content = self.client.get(url).content.decode()
        self.assertIn("Укажите военкомат.", get_content)
        resp = self.client.post(url, {"comment": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Обязательное поле.", resp.content.decode())
        self.assertEqual(Petition.objects.count(), 0)

    def test_subject_ignored_for_other_types(self):
        url = reverse("petitions:submit", args=[self.ordinary.pk])
        resp = self.client.post(url, {"subject": "X", "comment": ""})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Petition.objects.get().subject, "")


class CatalogTermTests(TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile
        self.client.force_login(self.student.user)

    def test_term_wording(self):
        for days in (1, 3, 5, 21):
            make_type(name=f"Тип {days}", days=days)
        content = self.client.get(reverse("petitions:catalog")).content.decode()
        self.assertIn("Срок: до 1 рабочего дня", content)
        self.assertIn("Срок: до 3 рабочих дней", content)
        self.assertIn("Срок: до 5 рабочих дней", content)
        self.assertIn("Срок: до 21 рабочего дня", content)
        self.assertNotIn("раб. дн.", content)

    def test_catch_all_last(self):
        make_type(name="Справка об обучении", kind="certificate", days=3)
        make_type(
            name="Другая справка",
            kind="certificate",
            days=5,
            comment_required=True,
            hint="h",
            subject_required=True,
        )
        make_type(name="Заявление об отпуске", kind="application", days=10)
        make_type(
            name="Другое заявление",
            kind="application",
            days=5,
            comment_required=True,
            hint="h",
            subject_required=True,
        )
        content = self.client.get(reverse("petitions:catalog")).content.decode()
        self.assertLess(content.index("Справка об обучении"), content.index("Другая справка"))
        self.assertLess(content.index("Заявление об отпуске"), content.index("Другое заявление"))


class SubjectDisplayTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.fac_y = make_faculty("FY")
        self.group = make_group(self.fac, "GX")
        self.group_y = make_group(self.fac_y, "GY")
        self.student = make_student("a", self.group, "SA").student_profile
        self.student_b = make_student("b", self.group_y, "SB").student_profile
        self.staff = make_staff("sx", self.fac)
        self.catch_all = make_type(
            name="Другая справка",
            days=5,
            comment_required=True,
            hint="h",
            subject_required=True,
        )
        self.petition = make_petition(self.student, self.catch_all)
        self.petition.subject = "Справка <b>о периоде</b>"
        self.petition.save(update_fields=["subject"])
        self.escaped = "Другая справка: Справка &lt;b&gt;о периоде&lt;/b&gt;"

    def test_student_list_and_detail(self):
        self.client.force_login(self.student.user)
        content = self.client.get(reverse("petitions:my_list")).content.decode()
        self.assertIn(self.escaped, content)
        self.assertNotIn("<b>о периоде</b>", content)
        detail = self.client.get(
            reverse("petitions:detail", args=[self.petition.public_id])
        ).content.decode()
        self.assertIn(self.escaped, detail)
        self.assertNotIn("<b>о периоде</b>", detail)

    def test_staff_queue_and_detail(self):
        self.client.force_login(self.staff)
        queue = self.client.get(reverse("petitions:staff_queue")).content.decode()
        self.assertIn(self.escaped, queue)
        detail = self.client.get(
            reverse("petitions:staff_detail", args=[self.petition.public_id])
        ).content.decode()
        self.assertIn(self.escaped, detail)

    def test_submitted_page(self):
        self.client.force_login(self.student.user)
        url = reverse("petitions:submit", args=[self.catch_all.pk])
        resp = self.client.post(url, {"subject": "Справка о периоде", "comment": "к"})
        self.assertEqual(resp.status_code, 302)
        submitted = self.client.get(resp["Location"])
        self.assertIn("Другая справка: Справка о периоде", submitted.content.decode())

    def test_other_student_cannot_see_subject(self):
        self.client.force_login(self.student_b.user)
        self.assertEqual(
            self.client.get(
                reverse("petitions:detail", args=[self.petition.public_id])
            ).status_code,
            404,
        )
        content = self.client.get(reverse("petitions:my_list")).content.decode()
        self.assertNotIn("Справка &lt;b&gt;о периоде&lt;/b&gt;", content)
        self.assertNotIn(str(self.petition.short_id), content)

    def test_plain_type_unchanged(self):
        plain = make_type(name="Справка об обучении")
        make_petition(self.student, plain)
        self.client.force_login(self.student.user)
        content = self.client.get(reverse("petitions:my_list")).content.decode()
        self.assertIn("Справка об обучении", content)
        self.assertNotIn("Справка об обучении:", content)


def _part(content: str, start_marker: str, end_marker: str) -> str:
    start = content.index(start_marker)
    return content[start : content.index(end_marker, start)]


SPACE_BEFORE_DOT = re.compile(r"[ \t\n]·")


class SeparatorTests(FrozenClockMixin, TestCase):
    """A separator dot is glued to the previous part (TASK-014-FIX)."""

    @classmethod
    def setUpTestData(cls):
        cls.fac = make_faculty("FX")
        cls.group = make_group(cls.fac, "GX")
        cls.student = make_student("a", cls.group, "SA").student_profile
        cls.staff = make_staff("sx", cls.fac)
        cls.ordinary = make_type(name="Справка об обучении")
        cls.catch_all = make_type(
            name="Другая справка",
            days=5,
            comment_required=True,
            hint="h",
            subject_required=True,
        )
        cls.p1 = make_petition(cls.student, cls.ordinary)
        cls.p2 = make_petition(cls.student, cls.catch_all)
        cls.p2.subject = "а" * 150
        cls.p2.save(update_fields=["subject"])
        change_status(cls.p1, cls.staff, "submitted", "in_progress")
        add_staff_comment(cls.p1, cls.staff, "Справка будет готова к пятнице.")
        cls.long_title = "Другая справка: " + "а" * 150

    def _student_list(self):
        self.client.force_login(self.student.user)
        return self.client.get(reverse("petitions:my_list")).content.decode()

    def _staff_queue(self):
        self.client.force_login(self.staff)
        return self.client.get(reverse("petitions:staff_queue")).content.decode()

    def test_no_space_before_dot_in_lists(self):
        for name, content in (("my_list", self._student_list()), ("queue", self._staff_queue())):
            with self.subTest(page=name):
                part = _part(content, '<ul class="petition-list">', "</ul>")
                self.assertIsNone(SPACE_BEFORE_DOT.search(part))
                rows = re.findall(r'<li class="petition">.*?</li>', part, re.S)
                self.assertEqual(len(rows), 2)
                for row in rows:
                    self.assertEqual(row.count("&nbsp;·"), 3)

    def test_no_space_before_dot_in_detail(self):
        pages = (
            (self.student.user, reverse("petitions:detail", args=[self.p1.public_id])),
            (self.staff, reverse("petitions:staff_detail", args=[self.p1.public_id])),
        )
        for user, url in pages:
            self.client.force_login(user)
            content = self.client.get(url).content.decode()
            with self.subTest(url=url):
                history = _part(content, "<ol>", "</ol>")
                self.assertIn("&nbsp;·", history)
                self.assertIsNone(SPACE_BEFORE_DOT.search(history))
                start = content.index("Справка будет готова к пятнице.")
                comments = content[content.rindex("<ul>", 0, start) : content.index("</ul>", start)]
                self.assertIn("&nbsp;·", comments)
                self.assertIsNone(SPACE_BEFORE_DOT.search(comments))

    def test_student_row_structure(self):
        content = self._student_list()
        link = (
            f'<a class="petition-title" href="/requests/{self.p2.public_id}/">{self.long_title}</a>'
        )
        self.assertIn(link, content)
        row = content[content.index(link) :]
        self.assertTrue(row[len(link) :].lstrip().startswith('<p class="petition-meta">'))
        self.assertIn(f'<span class="meta-item">№ {self.p2.short_id}&nbsp;·</span>', row)

    def test_staff_row_structure(self):
        content = self._staff_queue()
        subject = f'<p class="petition-subject">{self.long_title}</p>'
        self.assertIn(subject, content)
        row_start = content.rindex('<li class="petition">', 0, content.index(subject))
        row = content[row_start : content.index("</li>", row_start)]
        self.assertLess(row.index('<a class="petition-title"'), row.index(subject))
        self.assertLess(row.index(subject), row.index('<p class="petition-meta">'))
        self.assertIn("файлов: 0", row)

    def test_catalog_blocks(self):
        self.client.force_login(self.student.user)
        content = self.client.get(reverse("petitions:catalog")).content.decode()
        self.assertIn('<p class="catalog-term">Срок: до 5 рабочих дней</p>', content)
        self.assertIn('<a class="catalog-title"', content)
        main = _part(content, "<main", "</main>")
        self.assertNotIn(" — ", main)
        self.assertNotIn("·", main)

    def test_texts_and_links_kept(self):
        content = self._student_list()
        self.assertIn(f'href="/requests/{self.p1.public_id}/"', content)
        self.assertIn("В работе", content)
        self.assertIn("готовность:", content)
        queue = self._staff_queue()
        self.assertIn(f'href="/staff/requests/{self.p1.public_id}/"', queue)
        self.assertIn("GX", queue)
        self.assertIn("файлов:", queue)


class HardeningTests(FrozenClockMixin, TestCase):
    """TASK-016: PT1-F7 (hint escaped) and PT1-F8 (out-of-range type filter)."""

    HUGE = "9" * 25

    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile
        self.staff = make_staff("sx", self.fac)
        self.type = make_type()
        self.other_type = make_type(name="Другая")
        self.p1 = make_petition(self.student, self.type)
        self.p2 = make_petition(self.student, self.other_type)

    def test_comment_hint_escaped(self):
        hint = '<img src=x onerror="alert(1)"> & <b>жирный</b>'
        t = make_type(name="XSS", comment_required=True, hint=hint)
        self.client.force_login(self.student.user)
        content = self.client.get(reverse("petitions:submit", args=[t.pk])).content.decode()
        self.assertNotIn("<img src=x", content)
        self.assertNotIn("<b>жирный</b>", content)
        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt; &amp; &lt;b&gt;", content)

    def test_plain_hint_unchanged(self):
        t = make_type(name="Plain", comment_required=True, hint="Укажите причину «А»")
        form = PetitionForm(request_type=t)
        self.assertEqual(form.fields["comment"].help_text, "Укажите причину «А»")

    def _queue(self, type_value):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("petitions:staff_queue"), {"type": type_value})
        self.assertEqual(response.status_code, 200, type_value)
        return response.content.decode()

    def test_type_filter_valid(self):
        content = self._queue(str(self.type.pk))
        self.assertIn(str(self.p1.short_id), content)
        self.assertNotIn(str(self.p2.short_id), content)

    def test_type_filter_out_of_range_ignored(self):
        for value in (self.HUGE, "-1", "1e3", " 1", "\u0663", "0x1", ""):
            content = self._queue(value)
            self.assertIn(str(self.p1.short_id), content, value)
            self.assertIn(str(self.p2.short_id), content, value)

    def test_type_filter_18_digits_empty(self):
        content = self._queue("9" * 18)
        self.assertNotIn(str(self.p1.short_id), content)
        self.assertNotIn(str(self.p2.short_id), content)

    def test_huge_url_ids_404(self):
        self.client.force_login(self.student.user)
        self.assertEqual(self.client.get(f"/requests/new/{self.HUGE}/").status_code, 404)
        self.assertEqual(self.client.get(f"/map/floor/{self.HUGE}/").status_code, 404)
        self.client.force_login(self.staff)
        for path in (
            f"/staff/students/{self.HUGE}/",
            f"/staff/students/{self.HUGE}/grades/",
            f"/staff/schedule/{self.HUGE}/",
            f"/staff/schedule/{self.HUGE}/2026-11-16/",
        ):
            self.assertEqual(self.client.get(path).status_code, 404, path)
