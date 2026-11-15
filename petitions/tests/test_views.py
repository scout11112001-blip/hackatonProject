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
