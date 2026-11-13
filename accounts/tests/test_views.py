from django.test import TestCase
from django.urls import URLResolver, get_resolver, reverse

from accounts.models import User

from .helpers import make_faculty, make_group, make_staff, make_student


def _collect_public(names, patterns, namespaces):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            if pattern.app_name == "admin":
                continue
            ns = list(namespaces)
            if pattern.namespace:
                ns.append(pattern.namespace)
            elif pattern.app_name:
                ns.append(pattern.app_name)
            _collect_public(names, pattern.url_patterns, ns)
        else:
            callback = pattern.callback
            if getattr(callback, "login_required", True) is False:
                names.add(":".join(namespaces + [pattern.name]))
    return names


class AccessViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty_x = make_faculty("FX")
        cls.faculty_y = make_faculty("FY")
        cls.group_x = make_group(cls.faculty_x, "GX")
        cls.group_y = make_group(cls.faculty_y, "GY")
        cls.student_a = make_student("a", cls.group_x, "REC-A")
        cls.student_b = make_student("b", cls.group_y, "REC-B")
        cls.student_c = make_student("c", cls.group_x, "REC-C")
        cls.staff_x = make_staff("sx", cls.faculty_x)
        cls.staff_y = make_staff("sy", cls.faculty_y)

    def test_every_non_public_url_redirects_anonymous(self):
        pk_a = self.student_a.student_profile.pk
        for url in ["/", "/profile/", "/staff/students/", f"/staff/students/{pk_a}/"]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response["Location"].startswith("/login/?next="))

    def test_only_login_and_health_are_public(self):
        names = _collect_public(set(), get_resolver().url_patterns, [])
        self.assertEqual(names, {"accounts:login", "core:health"})

    def test_login_page_public(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("<form", content)
        self.assertIn(
            "Концепт для конкурса MGIMO AI Challenge. Не является официальным сервисом вуза. "
            "Все данные вымышлены.",
            content,
        )

    def test_login_success_redirects_to_profile(self):
        user = make_student("login-stu", self.group_x, "REC-LOGIN")
        user.set_password("Test-Pass-2026!")
        user.save()
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "login-stu", "password": "Test-Pass-2026!"},
        )
        self.assertRedirects(response, reverse("accounts:profile"))

    def test_logout_get_not_allowed(self):
        self.client.force_login(self.student_a)
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)

    def test_logout_post(self):
        self.client.force_login(self.student_a)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 302)

    def test_student_profile_shows_only_own_data(self):
        self.client.force_login(self.student_a)
        content = self.client.get(reverse("accounts:profile")).content.decode()
        self.assertIn("REC-A", content)
        self.assertIn(self.student_a.student_profile.full_name, content)
        self.assertNotIn("REC-B", content)
        self.assertNotIn("REC-C", content)

    def test_student_forbidden_on_staff_pages(self):
        self.client.force_login(self.student_a)
        pk_a = self.student_a.student_profile.pk
        pk_b = self.student_b.student_profile.pk
        for url in [
            reverse("accounts:staff_student_list"),
            reverse("accounts:staff_student_detail", args=[pk_b]),
            reverse("accounts:staff_student_detail", args=[pk_a]),
        ]:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_staff_list_scoped_to_faculty(self):
        self.client.force_login(self.staff_x)
        content = self.client.get(reverse("accounts:staff_student_list")).content.decode()
        self.assertIn(self.student_a.student_profile.full_name, content)
        self.assertIn(self.student_c.student_profile.full_name, content)
        self.assertNotIn(self.student_b.student_profile.full_name, content)

    def test_staff_detail_own_faculty(self):
        self.client.force_login(self.staff_x)
        pk_a = self.student_a.student_profile.pk
        response = self.client.get(reverse("accounts:staff_student_detail", args=[pk_a]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("REC-A", response.content.decode())

    def test_staff_detail_other_faculty_404(self):
        self.client.force_login(self.staff_x)
        pk_b = self.student_b.student_profile.pk
        response = self.client.get(reverse("accounts:staff_student_detail", args=[pk_b]))
        self.assertEqual(response.status_code, 404)

    def test_staff_detail_nonexistent_404(self):
        self.client.force_login(self.staff_x)
        response = self.client.get(reverse("accounts:staff_student_detail", args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_staff_never_sees_other_staff(self):
        self.client.force_login(self.staff_x)
        sy_name = self.staff_y.staff_profile.full_name
        pk_a = self.student_a.student_profile.pk
        for url in [
            reverse("accounts:profile"),
            reverse("accounts:staff_student_list"),
            reverse("accounts:staff_student_detail", args=[pk_a]),
        ]:
            self.assertNotIn(sy_name, self.client.get(url).content.decode())

    def test_staff_profile_shows_own_data(self):
        self.client.force_login(self.staff_x)
        content = self.client.get(reverse("accounts:profile")).content.decode()
        profile = self.staff_x.staff_profile
        self.assertIn(profile.full_name, content)
        self.assertIn(profile.position, content)
        self.assertIn(profile.faculty.name, content)

    def test_nav_depends_on_role(self):
        self.client.force_login(self.student_a)
        content_a = self.client.get(reverse("accounts:profile")).content.decode()
        self.assertNotIn("/staff/students/", content_a)
        self.assertIn('action="/logout/"', content_a)
        self.client.force_login(self.staff_x)
        content_x = self.client.get(reverse("accounts:profile")).content.decode()
        self.assertIn("/staff/students/", content_x)
        self.assertIn('action="/logout/"', content_x)

    def test_superuser_without_role(self):
        superuser = User.objects.create_superuser("root3", password=None)
        self.client.force_login(superuser)
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Профиль не заполнен", response.content.decode())
        self.assertEqual(self.client.get(reverse("accounts:staff_student_list")).status_code, 403)

    def test_staff_list_empty_state_markup(self):
        empty_faculty = make_faculty("FE")
        empty_staff = make_staff("se", empty_faculty)
        self.client.force_login(empty_staff)
        empty_content = self.client.get(reverse("accounts:staff_student_list")).content.decode()
        self.assertIn("<p>Студентов нет.</p>", empty_content)
        self.assertNotIn('class="student-list"', empty_content)

        self.client.force_login(self.staff_x)
        full_content = self.client.get(reverse("accounts:staff_student_list")).content.decode()
        self.assertIn('<ul class="student-list">', full_content)
        self.assertIn("<li>", full_content)
