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
