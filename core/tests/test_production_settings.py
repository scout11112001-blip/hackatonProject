import importlib.util
import os
from pathlib import Path
from types import ModuleType
from unittest import mock

import environ
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, SimpleTestCase, override_settings

SETTINGS_PATH = Path(settings.BASE_DIR) / "config" / "settings.py"

PRODUCTION_ENV = {
    "DEBUG": "false",
    "SECRET_KEY": "test-dummy-secret-key-not-for-production-0123456789abcdefghij",
    "ALLOWED_HOSTS": "testserver",
    "ADMIN_URL": "staff-panel/",
}


def _new_settings_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_hermetic_settings", SETTINGS_PATH)
    assert spec is not None and spec.loader is not None
    return importlib.util.module_from_spec(spec)


def _exec_settings(module: ModuleType, env_vars: dict[str, str]) -> None:
    with mock.patch.dict(os.environ, env_vars, clear=True):
        with mock.patch.object(environ.Env, "read_env", return_value=None):
            module.__spec__.loader.exec_module(module)


def _load_production_settings() -> ModuleType:
    module = _new_settings_module()
    _exec_settings(module, PRODUCTION_ENV)
    return module


class ProductionSettingsTests(SimpleTestCase):
    def test_debug_defaults_to_false(self):
        module = _new_settings_module()
        with self.assertRaisesMessage(ImproperlyConfigured, "SECRET_KEY"):
            _exec_settings(module, {})
        self.assertIs(module.DEBUG, False)

    def test_health_exempt_from_ssl_redirect_in_production(self):
        prod = _load_production_settings()
        self.assertIs(prod.SECURE_SSL_REDIRECT, True)
        with override_settings(
            SECURE_SSL_REDIRECT=prod.SECURE_SSL_REDIRECT,
            SECURE_REDIRECT_EXEMPT=prod.SECURE_REDIRECT_EXEMPT,
            SECURE_PROXY_SSL_HEADER=prod.SECURE_PROXY_SSL_HEADER,
        ):
            client = Client()
            response = client.get("/health/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok"})
            response = client.get("/")
            self.assertEqual(response.status_code, 301)
            self.assertEqual(response["Location"], "https://testserver/")

    def test_production_security_flags(self):
        prod = _load_production_settings()
        self.assertIs(prod.DEBUG, False)
        self.assertIs(prod.SESSION_COOKIE_SECURE, True)
        self.assertIs(prod.CSRF_COOKIE_SECURE, True)
        self.assertEqual(prod.SECURE_PROXY_SSL_HEADER, ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertEqual(prod.ALLOWED_HOSTS, ["testserver"])
        self.assertEqual(prod.ADMIN_URL, "staff-panel/")
        self.assertEqual(
            prod.STORAGES["staticfiles"]["BACKEND"],
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
        )
