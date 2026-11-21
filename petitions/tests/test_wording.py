"""TASK-017: "Документы" wording that agrees with the kind of a document."""

import ast
import re
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from core.testing import FrozenClockMixin
from petitions import wording
from petitions.models import (
    Petition,
    PetitionAttachment,
    PetitionComment,
    PetitionStatus,
    PetitionStatusChange,
    RequestType,
)
from petitions.services import change_status, submit_petition
from petitions.tests.helpers import make_petition, make_type

OLD_WORD = re.compile(r"[Зз]аявк|[Зз]аявок")
BASE = Path(settings.BASE_DIR)
APPS = (
    "accounts",
    "academics",
    "campusmap",
    "chat",
    "core",
    "notifications",
    "petitions",
    "schedule",
    "university",
)


class WordingUnitTests(SimpleTestCase):
    def test_generic_status_labels_masculine(self):
        self.assertEqual(
            dict(PetitionStatus.choices),
            {
                "submitted": "Подан",
                "in_progress": "В работе",
                "ready": "Готов",
                "issued": "Выдан",
                "rejected": "Отклонён",
            },
        )

    def test_status_label_by_kind(self):
        cases = {
            "certificate": ["Подана", "В работе", "Готова", "Выдана", "Отклонена"],
            "application": ["Подано", "В работе", "Готово", "Выдано", "Отклонено"],
        }
        statuses = ["submitted", "in_progress", "ready", "issued", "rejected"]
        for kind, labels in cases.items():
            for status, label in zip(statuses, labels, strict=True):
                self.assertEqual(wording.status_label(status, kind), label, (kind, status))

    def test_status_label_unknown_kind_is_generic(self):
        self.assertEqual(wording.status_label("ready", "other"), "Готов")

    def test_action_labels(self):
        self.assertEqual(wording.action_label("ready", "certificate"), "Отметить готовой")
        self.assertEqual(wording.action_label("issued", "certificate"), "Отметить выданной")
        self.assertEqual(wording.action_label("ready", "application"), "Отметить готовым")
        self.assertEqual(wording.action_label("issued", "application"), "Отметить выданным")
        self.assertEqual(wording.action_label("in_progress", "application"), "Взять в работу")
        self.assertEqual(wording.action_label("rejected", "application"), "Отклонить")

    def test_plural(self):
        forms = wording.DOCUMENT_FORMS
        expected = {
            1: "документ",
            2: "документа",
            3: "документа",
            4: "документа",
            5: "документов",
            11: "документов",
            12: "документов",
            14: "документов",
            21: "документ",
            22: "документа",
            25: "документов",
            111: "документов",
        }
        for n, form in expected.items():
            self.assertEqual(wording.plural_ru(n, forms), form, n)

    def test_notification_titles(self):
        cert = {
            "in_progress": "«Х» взята в работу",
            "ready": "«Х» готова — заберите её в деканате",
            "issued": "«Х» выдана",
            "rejected": "«Х» отклонена",
            "submitted": "«Х»: статус «Подана»",
        }
        appl = {
            "in_progress": "«Х» взято в работу",
            "ready": "«Х» готово — заберите его в деканате",
            "issued": "«Х» выдано",
            "rejected": "«Х» отклонено",
            "submitted": "«Х»: статус «Подано»",
        }
        for status, title in cert.items():
            self.assertEqual(wording.notification_title(status, "certificate", "Х"), title)
        for status, title in appl.items():
            self.assertEqual(wording.notification_title(status, "application", "Х"), title)

    def test_admin_names(self):
        self.assertEqual(apps.get_app_config("petitions").verbose_name, "Документы")
        self.assertEqual(Petition._meta.verbose_name, "документ")
        self.assertEqual(Petition._meta.verbose_name_plural, "документы")
        self.assertEqual(RequestType._meta.verbose_name, "вид документа")
        self.assertEqual(RequestType._meta.verbose_name_plural, "виды документов")
        self.assertEqual(PetitionAttachment._meta.verbose_name, "файл к документу")
        self.assertEqual(PetitionAttachment._meta.verbose_name_plural, "файлы к документам")
        for model in (PetitionAttachment, PetitionStatusChange, PetitionComment):
            self.assertEqual(model._meta.get_field("petition").verbose_name, "документ")
        self.assertEqual(Petition._meta.get_field("request_type").verbose_name, "вид документа")


class NoOldWordTests(SimpleTestCase):
    """No user-visible "заявка" is left; "заявление" (a kind) stays."""

    def test_templates(self):
        paths = sorted(BASE.glob("templates/**/*.html")) + sorted(
            BASE.glob("*/templates/**/*.html")
        )
        self.assertGreater(len(paths), 30)
        for path in paths:
            self.assertIsNone(OLD_WORD.search(path.read_text(encoding="utf-8")), path)

    def test_python_strings(self):
        checked = 0
        for app in APPS:
            for path in sorted((BASE / app).rglob("*.py")):
                if "tests" in path.parts or "migrations" in path.parts:
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        checked += 1
                        self.assertIsNone(OLD_WORD.search(node.value), f"{path}: {node.value}")
        self.assertGreater(checked, 500)

    def test_static_js(self):
        for path in sorted((BASE / "static" / "js").glob("*.js")):
            self.assertIsNone(OLD_WORD.search(path.read_text(encoding="utf-8")), path)


class PagesWordingTests(FrozenClockMixin, TestCase):
    def setUp(self):
        self.fac = make_faculty("FX")
        self.group = make_group(self.fac, "GX")
        self.student = make_student("a", self.group, "SA").student_profile
        self.staff = make_staff("sx", self.fac)
        self.cert = make_type(name="Справка Х")
        self.appl = make_type(name="Заявление Х", kind="application", days=5)
        self.p_cert = make_petition(self.student, self.cert)
        self.p_appl = make_petition(self.student, self.appl)

    def _student_get(self, url):
        self.client.force_login(self.student.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        return response.content.decode()

    def _staff_get(self, url):
        self.client.force_login(self.staff)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, url)
        return response.content.decode()

    def test_nav_and_titles(self):
        content = self._student_get(reverse("petitions:my_list"))
        self.assertIn('aria-current="page">Документы</a>', content)
        self.assertIn("<h1>Мои документы</h1>", content)
        self.assertIn(">Оформить документ</a>", content)
        content = self._student_get(reverse("petitions:catalog"))
        self.assertIn("<h1>Оформить документ</h1>", content)
        content = self._staff_get(reverse("petitions:staff_queue"))
        self.assertIn('aria-current="page">Документы</a>', content)
        self.assertIn("<h1>Документы</h1>", content)
        self.assertIn('<label for="type">Вид документа</label>', content)

    def test_submit_buttons_by_kind(self):
        content = self._student_get(reverse("petitions:submit", args=[self.cert.pk]))
        self.assertIn('<button type="submit">Заказать справку</button>', content)
        content = self._student_get(reverse("petitions:submit", args=[self.appl.pk]))
        self.assertIn('<button type="submit">Подать заявление</button>', content)

    def test_submitted_page_by_kind(self):
        content = self._student_get(reverse("petitions:submitted", args=[self.p_cert.public_id]))
        self.assertIn("<h1>Справка заказана</h1>", content)
        self.assertIn(">К справке</a>", content)
        self.assertIn(">Мои документы</a>", content)
        content = self._student_get(reverse("petitions:submitted", args=[self.p_appl.public_id]))
        self.assertIn("<h1>Заявление подано</h1>", content)
        self.assertIn(">К заявлению</a>", content)

    def test_student_list_and_detail_status_by_kind(self):
        change_status(self.p_appl, self.staff, "submitted", "in_progress")
        change_status(self.p_appl, self.staff, "in_progress", "ready")
        content = self._student_get(reverse("petitions:my_list"))
        self.assertIn('status--submitted">Подана</span>', content)
        self.assertIn('status--ready">Готово</span>', content)
        content = self._student_get(reverse("petitions:detail", args=[self.p_appl.public_id]))
        self.assertIn('<p class="status status--ready">Готово</p>', content)
        self.assertIn("<p>Подано: ", content)
        self.assertIn("Подано → В работе", content)
        self.assertIn("В работе → Готово", content)
        content = self._student_get(reverse("petitions:detail", args=[self.p_cert.public_id]))
        self.assertIn("<p>Подана: ", content)

    def test_staff_pages_by_kind(self):
        content = self._staff_get(reverse("petitions:staff_queue"))
        self.assertIn('<option value="submitted">Подан</option>', content)
        self.assertIn('<option value="rejected">Отклонён</option>', content)
        self.assertIn('status--submitted">Подано</span>', content)
        self.assertIn('status--submitted">Подана</span>', content)
        content = self._staff_get(reverse("petitions:staff_detail", args=[self.p_cert.public_id]))
        self.assertIn(f"<h1>Справка № {self.p_cert.short_id}</h1>", content)
        self.assertIn("<h2>Документ</h2>", content)
        change_status(self.p_appl, self.staff, "submitted", "in_progress")
        content = self._staff_get(reverse("petitions:staff_detail", args=[self.p_appl.public_id]))
        self.assertIn(f"<h1>Заявление № {self.p_appl.short_id}</h1>", content)
        self.assertIn(">Отметить готовым</button>", content)
        change_status(self.p_cert, self.staff, "submitted", "in_progress")
        content = self._staff_get(reverse("petitions:staff_detail", args=[self.p_cert.public_id]))
        self.assertIn(">Отметить готовой</button>", content)

    def test_flash_message_by_kind(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("petitions:staff_transition", args=[self.p_appl.public_id]),
            {"expected_status": "submitted", "new_status": "in_progress"},
            follow=True,
        )
        self.assertIn("Статус изменён: В работе.", response.content.decode())
        response = self.client.post(
            reverse("petitions:staff_transition", args=[self.p_appl.public_id]),
            {"expected_status": "in_progress", "new_status": "ready"},
            follow=True,
        )
        self.assertIn("Статус изменён: Готово.", response.content.decode())

    def test_comment_required_error_by_kind(self):
        # The form shows Django's "Обязательное поле." (TASK-014-FIX); the service message
        # (also used by PetitionForm.clean_comment) agrees with the kind.
        cert = make_type(name="Справка К", comment_required=True, hint="Причина")
        appl = make_type(name="Заявление К", kind="application", comment_required=True, hint="П")
        with self.assertRaises(ValidationError) as cm:
            submit_petition(self.student, cert, "", [])
        self.assertIn("Для этой справки комментарий обязателен.", cm.exception.messages)
        with self.assertRaises(ValidationError) as cm:
            submit_petition(self.student, appl, "", [])
        self.assertIn("Для этого заявления комментарий обязателен.", cm.exception.messages)

    def test_subject_hint_by_kind(self):
        cert = make_type(name="Другая С", comment_required=True, hint="h", subject_required=True)
        appl = make_type(
            name="Другое З",
            kind="application",
            comment_required=True,
            hint="h",
            subject_required=True,
        )
        content = self._student_get(reverse("petitions:submit", args=[cert.pk]))
        self.assertIn("Что именно нужно, например: «Справка о периоде обучения».", content)
        content = self._student_get(reverse("petitions:submit", args=[appl.pk]))
        self.assertIn(
            "Что именно нужно, например: «Заявление на индивидуальный учебный план».", content
        )
        self.assertNotIn("Справка о периоде обучения", content)

    def test_notifications_by_kind(self):
        change_status(self.p_cert, self.staff, "submitted", "in_progress")
        change_status(self.p_appl, self.staff, "submitted", "in_progress")
        change_status(self.p_appl, self.staff, "in_progress", "ready")
        content = self._student_get(reverse("notifications:feed"))
        self.assertIn("«Справка Х» взята в работу", content)
        self.assertIn("«Заявление Х» взято в работу", content)
        self.assertIn("«Заявление Х» готово — заберите его в деканате", content)
        self.assertIn("Документы&nbsp;·", content)
