"""Tests for private file storage and the test runner."""

import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, TestCase, override_settings

from core.storage import get_private_storage
from core.tests.test_production_settings import PRODUCTION_ENV, _exec_settings, _new_settings_module


class PrivateStorageTests(TestCase):
    def test_location_follows_setting(self):
        tmp = tempfile.mkdtemp(prefix="priv-")
        self.addCleanup(shutil.rmtree, tmp, True)
        with override_settings(PRIVATE_MEDIA_ROOT=tmp):
            self.assertEqual(get_private_storage().location, tmp)

    def test_url_raises(self):
        with self.assertRaisesMessage(ValueError, "no public URL"):
            get_private_storage().url("request_attachments/ab/cd.pdf")

    def test_existing_name_is_not_overwritten(self):
        tmp = tempfile.mkdtemp(prefix="priv-")
        self.addCleanup(shutil.rmtree, tmp, True)
        with override_settings(PRIVATE_MEDIA_ROOT=tmp):
            storage = get_private_storage()
            name = storage.save("a/x.pdf", ContentFile(b"%PDF-first"))
            with self.assertRaises(FileExistsError):
                storage.save(name, ContentFile(b"%PDF-second"))
            with storage.open(name, "rb") as fh:
                self.assertEqual(fh.read(), b"%PDF-first")


class TestRunnerTests(SimpleTestCase):
    def test_test_runner_uses_temp_dir(self):
        root = Path(settings.PRIVATE_MEDIA_ROOT)
        base = Path(settings.BASE_DIR)
        self.assertNotEqual(root, base)
        self.assertNotIn(base, root.parents)
        self.assertTrue(root.is_dir())


class PrivateRootSettingsTests(SimpleTestCase):
    def _load(self, extra: dict[str, str]):
        module = _new_settings_module()
        _exec_settings(module, {**PRODUCTION_ENV, **extra})
        return module

    def test_private_root_default(self):
        mod = self._load({"PRIVATE_MEDIA_ROOT": ""})
        self.assertEqual(mod.PRIVATE_MEDIA_ROOT, mod.BASE_DIR / "private_media")

    def test_private_root_unset(self):
        mod = self._load({})
        self.assertEqual(mod.PRIVATE_MEDIA_ROOT, mod.BASE_DIR / "private_media")

    def test_private_root_set(self):
        mod = self._load({"PRIVATE_MEDIA_ROOT": "/srv/private"})
        self.assertEqual(mod.PRIVATE_MEDIA_ROOT, Path("/srv/private"))
