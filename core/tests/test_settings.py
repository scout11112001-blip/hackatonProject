import os
from unittest import skipUnless

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse


class SettingsTests(SimpleTestCase):
    def test_locale(self):
        self.assertEqual(settings.LANGUAGE_CODE, "ru")
        self.assertEqual(settings.TIME_ZONE, "Europe/Moscow")
        self.assertIs(settings.USE_TZ, True)

    def test_password_validators_enabled(self):
        names = {v["NAME"] for v in settings.AUTH_PASSWORD_VALIDATORS}
        expected = {
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
            "django.contrib.auth.password_validation.MinimumLengthValidator",
            "django.contrib.auth.password_validation.CommonPasswordValidator",
            "django.contrib.auth.password_validation.NumericPasswordValidator",
        }
        self.assertEqual(names, expected)

    def test_admin_mounted_at_admin_url(self):
        self.assertEqual(reverse("admin:index"), "/" + settings.ADMIN_URL)

    def test_whitenoise_after_security_middleware(self):
        self.assertEqual(
            settings.MIDDLEWARE.index("whitenoise.middleware.WhiteNoiseMiddleware"),
            settings.MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
        )

    def test_only_w021_silenced(self):
        self.assertEqual(settings.SILENCED_SYSTEM_CHECKS, ["security.W021"])

    def test_custom_user_model(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")

    def test_login_required_middleware_after_auth(self):
        self.assertEqual(
            settings.MIDDLEWARE.index("django.contrib.auth.middleware.LoginRequiredMiddleware"),
            settings.MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware")
            + 1,
        )

    @skipUnless(
        "LOGIN_FAILURE_LIMIT" not in os.environ
        and "LOGIN_LOCKOUT_SECONDS" not in os.environ
        and "CLIENT_IP_HEADER" not in os.environ,
        "login throttle env vars are set",
    )
    def test_login_throttle_defaults(self):
        self.assertEqual(settings.LOGIN_FAILURE_LIMIT, 5)
        self.assertEqual(settings.LOGIN_LOCKOUT_SECONDS, 900)
        self.assertEqual(settings.CLIENT_IP_HEADER, "")
