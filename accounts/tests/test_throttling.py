from datetime import datetime, timedelta
from unittest import mock

from django.http import HttpRequest
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import LoginThrottle, User
from accounts.throttling import (
    UNKNOWN_IP,
    get_client_ip,
    is_locked,
    normalize_username,
    register_failure,
    throttle_ip,
)


@override_settings(LOGIN_FAILURE_LIMIT=3, LOGIN_LOCKOUT_SECONDS=900, CLIENT_IP_HEADER="")
class LoginThrottleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="u1", role=User.Role.STUDENT)
        cls.user.set_password("Test-Pass-2026!")
        cls.user.save()

    def _post_login(self, username, password, **extra):
        return self.client.post(
            reverse("accounts:login"), {"username": username, "password": password}, **extra
        )

    def test_lockout_after_limit(self):
        for _ in range(3):
            self._post_login("u1", "wrong")
        response = self._post_login("u1", "Test-Pass-2026!")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Слишком много неудачных попыток", response.content.decode())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_lock_is_per_ip(self):
        for _ in range(3):
            self._post_login("u1", "wrong", REMOTE_ADDR="10.0.0.1")
        response = self._post_login("u1", "Test-Pass-2026!", REMOTE_ADDR="10.0.0.2")
        self.assertEqual(response.status_code, 302)

    def test_lock_expires(self):
        t0 = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.get_current_timezone())
        with mock.patch("django.utils.timezone.now", return_value=t0):
            for _ in range(3):
                self._post_login("u1", "wrong")
        t1 = t0 + timedelta(seconds=901)
        with mock.patch("django.utils.timezone.now", return_value=t1):
            response = self._post_login("u1", "Test-Pass-2026!")
        self.assertEqual(response.status_code, 302)

    def test_success_resets_counter(self):
        for _ in range(2):
            self._post_login("u1", "wrong")
        self._post_login("u1", "Test-Pass-2026!")
        self.client.post(reverse("accounts:logout"))
        for _ in range(2):
            self._post_login("u1", "wrong")
        response = self._post_login("u1", "Test-Pass-2026!")
        self.assertEqual(response.status_code, 302)

    def test_messages_do_not_reveal_user_existence(self):
        r1 = self._post_login("u1", "wrong")
        r2 = self._post_login("nobody", "wrong")
        err1 = list(r1.context["form"].non_field_errors())
        err2 = list(r2.context["form"].non_field_errors())
        self.assertEqual(err1, err2)

    def test_xff_ignored_by_default(self):
        for xff in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
            self._post_login("u1", "wrong", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR=xff)
        response = self._post_login("u1", "Test-Pass-2026!", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Слишком много неудачных попыток", response.content.decode())

    @override_settings(CLIENT_IP_HEADER="HTTP_X_FORWARDED_FOR")
    def test_xff_used_when_enabled(self):
        for _ in range(3):
            self._post_login("u1", "wrong", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="5.5.5.5")
        response = self._post_login(
            "u1", "Test-Pass-2026!", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="6.6.6.6"
        )
        self.assertEqual(response.status_code, 302)

    def test_admin_login_protected(self):
        User.objects.create_superuser("root", password="Admin-Pass-2026!")
        for _ in range(3):
            self.client.post(reverse("admin:login"), {"username": "root", "password": "wrong"})
        response = self.client.post(
            reverse("admin:login"), {"username": "root", "password": "Admin-Pass-2026!"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Слишком много неудачных попыток", response.content.decode())

    def test_ipv6_same_64_shares_lock(self):
        # TASK-016 (PT1-F2): a new address in the same /64 does not get new attempts.
        for host in ("1", "2", "3"):
            self._post_login("u1", "wrong", REMOTE_ADDR=f"2001:db8:1:2::{host}")
        response = self._post_login("u1", "Test-Pass-2026!", REMOTE_ADDR="2001:db8:1:2:ffff::9")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Слишком много неудачных попыток", response.content.decode())
        self.assertTrue(LoginThrottle.objects.filter(ip_address="2001:db8:1:2::").exists())

    def test_ipv6_other_64_not_locked(self):
        for _ in range(3):
            self._post_login("u1", "wrong", REMOTE_ADDR="2001:db8:1:2::1")
        response = self._post_login("u1", "Test-Pass-2026!", REMOTE_ADDR="2001:db8:1:3::1")
        self.assertEqual(response.status_code, 302)

    def test_no_lock_across_ipv4_addresses(self):
        # User decision (plan.md 6b): no per-account lock across addresses.
        for host in ("1", "2", "3", "4", "5", "6"):
            self._post_login("u1", "wrong", REMOTE_ADDR=f"10.0.{host}.1")
        response = self._post_login("u1", "Test-Pass-2026!", REMOTE_ADDR="10.0.9.1")
        self.assertEqual(response.status_code, 302)

    def test_locked_does_not_authenticate(self):
        for _ in range(3):
            self._post_login("u1", "wrong")
        with mock.patch("django.contrib.auth.forms.authenticate") as auth_mock:
            self._post_login("u1", "Test-Pass-2026!")
        auth_mock.assert_not_called()


class ThrottlingUnitTests(TestCase):
    def test_normalize_username(self):
        self.assertEqual(normalize_username("  Student1 "), "student1")

    def test_get_client_ip_none(self):
        self.assertEqual(get_client_ip(None), UNKNOWN_IP)

    def test_get_client_ip_default_ignores_headers(self):
        request = RequestFactory().get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.1.1.1")
        self.assertEqual(get_client_ip(request), "10.0.0.1")

    @override_settings(CLIENT_IP_HEADER="HTTP_X_REAL_IP")
    def test_get_client_ip_real_ip(self):
        request = RequestFactory().get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_REAL_IP="5.5.5.5")
        self.assertEqual(get_client_ip(request), "5.5.5.5")

    @override_settings(CLIENT_IP_HEADER="HTTP_X_FORWARDED_FOR")
    def test_get_client_ip_xff_last(self):
        request = RequestFactory().get(
            "/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR="1.1.1.1, 2.2.2.2"
        )
        self.assertEqual(get_client_ip(request), "2.2.2.2")

    @override_settings(CLIENT_IP_HEADER="HTTP_X_REAL_IP")
    def test_get_client_ip_invalid_header_falls_back(self):
        request = RequestFactory().get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_REAL_IP="not-an-ip")
        self.assertEqual(get_client_ip(request), "10.0.0.1")

    def test_get_client_ip_missing_remote_addr(self):
        request = HttpRequest()
        request.META = {}
        self.assertEqual(get_client_ip(request), UNKNOWN_IP)

    @override_settings(LOGIN_FAILURE_LIMIT=3, LOGIN_LOCKOUT_SECONDS=900)
    def test_register_failure_sets_lock_at_limit(self):
        t0 = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.get_current_timezone())
        for _ in range(3):
            register_failure("u1", "10.0.0.1", t0)
        row = LoginThrottle.objects.get(username_key="u1", ip_address="10.0.0.1")
        self.assertEqual(row.failures, 3)
        self.assertEqual(row.locked_until, t0 + timedelta(seconds=900))
        self.assertTrue(is_locked("u1", "10.0.0.1", t0))

    @override_settings(LOGIN_FAILURE_LIMIT=3, LOGIN_LOCKOUT_SECONDS=900)
    def test_register_failure_old_window_restarts(self):
        t0 = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.get_current_timezone())
        register_failure("u1", "10.0.0.1", t0)
        t_late = t0 + timedelta(seconds=901)
        register_failure("u1", "10.0.0.1", t_late)
        row = LoginThrottle.objects.get(username_key="u1", ip_address="10.0.0.1")
        self.assertEqual(row.failures, 1)


class ThrottleIpTests(SimpleTestCase):
    def test_ipv4_unchanged(self):
        self.assertEqual(throttle_ip("203.0.113.7"), "203.0.113.7")

    def test_ipv6_network_64(self):
        self.assertEqual(throttle_ip("2001:db8:1:2:aaaa:bbbb:cccc:dddd"), "2001:db8:1:2::")
        self.assertEqual(throttle_ip("2001:DB8:1:2::1"), "2001:db8:1:2::")

    def test_ipv4_mapped_ipv6(self):
        self.assertEqual(throttle_ip("::ffff:203.0.113.7"), "203.0.113.7")

    def test_loopback_and_unknown(self):
        self.assertEqual(throttle_ip("::1"), "::")
        self.assertEqual(throttle_ip(UNKNOWN_IP), UNKNOWN_IP)
        self.assertEqual(throttle_ip("not-an-ip"), UNKNOWN_IP)
