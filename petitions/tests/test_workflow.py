from django.test import SimpleTestCase

from petitions.wording import ACTION_LABELS
from petitions.workflow import (
    OPEN_STATUSES,
    TRANSITIONS,
    allowed_transitions,
    can_transition,
)


class WorkflowTests(SimpleTestCase):
    STATUSES = ["submitted", "in_progress", "ready", "issued", "rejected"]

    def test_allowed_transitions_exact(self):
        expected = {
            "submitted": ("in_progress", "rejected"),
            "in_progress": ("ready", "rejected"),
            "ready": ("issued",),
            "issued": (),
            "rejected": (),
        }
        for status in self.STATUSES:
            self.assertEqual(allowed_transitions(status), expected[status])

    def test_can_transition_allowed(self):
        for from_s, to_s in [
            ("submitted", "in_progress"),
            ("submitted", "rejected"),
            ("in_progress", "ready"),
            ("in_progress", "rejected"),
            ("ready", "issued"),
        ]:
            self.assertTrue(can_transition(from_s, to_s), (from_s, to_s))

    def test_can_transition_disallowed_matrix(self):
        allowed = {
            ("submitted", "in_progress"),
            ("submitted", "rejected"),
            ("in_progress", "ready"),
            ("in_progress", "rejected"),
            ("ready", "issued"),
        }
        for from_s in self.STATUSES:
            for to_s in self.STATUSES:
                if (from_s, to_s) in allowed:
                    continue
                self.assertFalse(can_transition(from_s, to_s), (from_s, to_s))

    def test_final_statuses(self):
        self.assertEqual(allowed_transitions("issued"), ())
        self.assertEqual(allowed_transitions("rejected"), ())

    def test_every_target_has_label(self):
        targets = {t for ts in TRANSITIONS.values() for t in ts}
        # TASK-017: the labels live in petitions.wording, one set per kind.
        for labels in ACTION_LABELS.values():
            for t in targets:
                self.assertIn(t, labels)

    def test_open_statuses_exact(self):
        self.assertEqual(OPEN_STATUSES, frozenset({"submitted", "in_progress"}))
