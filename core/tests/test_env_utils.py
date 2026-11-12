from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.env_utils import (
    DEV_SECRET_KEY,
    resolve_admin_url,
    resolve_secret_key,
)


class ResolveSecretKeyTests(SimpleTestCase):
    def test_returns_given_key(self):
        self.assertEqual(resolve_secret_key("abc...", False), "abc...")

    def test_strips_whitespace(self):
        self.assertEqual(resolve_secret_key("  key  ", False), "key")

    def test_dev_fallback_when_debug(self):
        self.assertEqual(resolve_secret_key("", True), DEV_SECRET_KEY)

    def test_missing_key_in_production_raises(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "SECRET_KEY"):
            resolve_secret_key("", False)

    def test_whitespace_key_in_production_raises(self):
        with self.assertRaises(ImproperlyConfigured):
            resolve_secret_key("   ", False)


class ResolveAdminUrlTests(SimpleTestCase):
    def test_default_in_debug(self):
        self.assertEqual(resolve_admin_url("", True), "admin/")

    def test_missing_in_production_raises(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "ADMIN_URL"):
            resolve_admin_url("", False)

    def test_adds_trailing_slash(self):
        self.assertEqual(resolve_admin_url("staff", False), "staff/")

    def test_strips_slashes_and_spaces(self):
        self.assertEqual(resolve_admin_url(" /staff/ ", False), "staff/")

    def test_nested_path_allowed(self):
        self.assertEqual(resolve_admin_url("x/staff", False), "x/staff/")

    def test_invalid_characters_raise(self):
        for bad in ["a//b", "../x", "st aff", "staff?x=1"]:
            with self.subTest(bad=bad):
                with self.assertRaises(ImproperlyConfigured):
                    resolve_admin_url(bad, False)
