"""TASK-017: data migration 0005 renames "Справка в военкомат" in place."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [("petitions", "0004_documents_wording")]
AFTER = [("petitions", "0005_admission_certificate")]


class AdmissionCertificateMigrationTests(TransactionTestCase):
    def _migrate(self, target):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(target)
        return executor.loader.project_state(target).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def _make_old(self, apps, **extra):
        RequestType = apps.get_model("petitions", "RequestType")
        values = {
            "name": "Справка в военкомат",
            "kind": "certificate",
            "processing_days": 3,
            "comment_required": True,
            "comment_hint": "Укажите военкомат.",
            "description": "Справка для военного комиссариата.",
            "subject_required": False,
            "is_active": True,
        }
        values.update(extra)
        return RequestType.objects.create(**values)

    def test_rename_in_place(self):
        old_apps = self._migrate(BEFORE)
        old = self._make_old(old_apps)
        new_apps = self._migrate(AFTER)
        RequestType = new_apps.get_model("petitions", "RequestType")
        row = RequestType.objects.get(pk=old.pk)
        self.assertEqual(row.name, "Справка о поступлении")
        self.assertFalse(row.comment_required)
        self.assertEqual(row.comment_hint, "Можно указать, куда нужна справка.")
        self.assertEqual(row.description, "Подтверждает зачисление в университет.")
        self.assertEqual(row.processing_days, 3)
        self.assertEqual(row.kind, "certificate")
        self.assertTrue(row.is_active)
        self.assertFalse(RequestType.objects.filter(name="Справка в военкомат").exists())

    def test_backwards(self):
        old_apps = self._migrate(BEFORE)
        old = self._make_old(old_apps)
        self._migrate(AFTER)
        back_apps = self._migrate(BEFORE)
        row = back_apps.get_model("petitions", "RequestType").objects.get(pk=old.pk)
        self.assertEqual(row.name, "Справка в военкомат")
        self.assertTrue(row.comment_required)

    def test_new_name_taken_hides_old(self):
        old_apps = self._migrate(BEFORE)
        old = self._make_old(old_apps)
        self._make_old(
            old_apps, name="Справка о поступлении", comment_required=False, comment_hint=""
        )
        new_apps = self._migrate(AFTER)
        RequestType = new_apps.get_model("petitions", "RequestType")
        self.assertFalse(RequestType.objects.get(pk=old.pk).is_active)
        self.assertEqual(RequestType.objects.filter(name="Справка о поступлении").count(), 1)

    def test_no_old_type_is_noop(self):
        self._migrate(BEFORE)
        new_apps = self._migrate(AFTER)
        RequestType = new_apps.get_model("petitions", "RequestType")
        self.assertFalse(RequestType.objects.filter(name__startswith="Справка").exists())
