import os
from datetime import date
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from academics.demo import seed_academics_demo
from accounts.demo import seed_demo_data
from core.storage import get_private_storage
from core.testing import FrozenClockMixin
from petitions.demo import seed_petitions_demo
from petitions.models import (
    Petition,
    PetitionAttachment,
    PetitionComment,
    PetitionStatusChange,
    RequestType,
)
from petitions.workflow import can_transition
from schedule.demo import seed_schedule_demo

PASSWORD = "Local-Demo-Pass-2026!"
D = date(2026, 11, 18)


class PetitionsDemoTests(FrozenClockMixin, TestCase):
    def setUp(self):
        seed_demo_data(PASSWORD)
        seed_schedule_demo(D)
        seed_academics_demo(D)
        seed_petitions_demo(D)

    def _count_files(self):
        root = get_private_storage().location
        count = 0
        for _dirpath, _dirnames, filenames in os.walk(root):
            count += len(filenames)
        return count

    def test_types_exact(self):
        expected = {
            ("Справка об обучении", "certificate", 3, False),
            ("Справка для стипендиального отдела", "certificate", 3, True),
            ("Заявление на повторную промежуточную аттестацию", "application", 10, True),
            ("Заявление на академический отпуск", "application", 15, True),
        }
        types = RequestType.objects.all()
        self.assertEqual(types.count(), 4)
        for t in types:
            self.assertIn((t.name, t.kind, t.processing_days, t.comment_required), expected)

    def test_every_status_present(self):
        statuses = set(Petition.objects.values_list("status", flat=True))
        self.assertEqual(statuses, {"submitted", "in_progress", "ready", "issued", "rejected"})

    def test_each_faculty_has_waiting_request(self):
        for code in ("FDD", "FAE"):
            count = Petition.objects.filter(
                status="submitted", student__group__program__faculty__code=code
            ).count()
            self.assertGreaterEqual(count, 1)

    def test_history_consistent(self):
        for petition in Petition.objects.all():
            history = list(petition.history.order_by("created_at", "pk"))
            self.assertTrue(history)
            first = history[0]
            self.assertEqual(first.from_status, "")
            self.assertEqual(first.to_status, "submitted")
            self.assertEqual(first.actor, petition.student.user)
            for prev, cur in zip(history, history[1:], strict=False):
                self.assertEqual(cur.from_status, prev.to_status)
            self.assertEqual(history[-1].to_status, petition.status)
            for step in history:
                if step.from_status:
                    self.assertTrue(can_transition(step.from_status, step.to_status))

    def test_demo_files_private_and_valid(self):
        atts = PetitionAttachment.objects.all()
        self.assertEqual(atts.count(), 3)
        for att in atts:
            self.assertRegex(att.file.name, r"^request_attachments/[0-9a-f]{2}/[0-9a-f]{32}\.pdf$")
            with att.file.open("rb") as fh:
                self.assertTrue(fh.read().startswith(b"%PDF-"))

    def test_idempotent(self):
        before = (
            Petition.objects.count(),
            PetitionStatusChange.objects.count(),
            PetitionComment.objects.count(),
            PetitionAttachment.objects.count(),
            self._count_files(),
        )
        seed_petitions_demo(D)
        after = (
            Petition.objects.count(),
            PetitionStatusChange.objects.count(),
            PetitionComment.objects.count(),
            PetitionAttachment.objects.count(),
            self._count_files(),
        )
        self.assertEqual(before, after)

    def test_command_output(self):
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": PASSWORD}):
            out = StringIO()
            call_command("seed_demo", stdout=out)
        self.assertIn("Requests ready", out.getvalue())
