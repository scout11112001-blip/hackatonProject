from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_status_and_templates(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertTemplateUsed(response, "base.html")

    def test_home_base_layout(self):
        response = self.client.get(reverse("core:home"))
        content = response.content.decode()
        self.assertIn('lang="ru"', content)
        self.assertIn('name="viewport"', content)
        self.assertIn("<header", content)
        self.assertIn("<nav", content)
        self.assertIn("<main", content)
        self.assertIn("<footer", content)
        self.assertIn(
            "Концепт для конкурса MGIMO AI Challenge. Не является официальным сервисом вуза. "
            "Все данные вымышлены.",
            content,
        )

    def test_home_css_layers_in_order(self):
        response = self.client.get(reverse("core:home"))
        content = response.content.decode()
        tokens = content.find("css/tokens.css")
        base = content.find("css/base.css")
        theme = content.find("css/theme.css")
        self.assertNotEqual(tokens, -1)
        self.assertNotEqual(base, -1)
        self.assertNotEqual(theme, -1)
        self.assertLess(tokens, base)
        self.assertLess(base, theme)

    def test_home_has_no_external_resources(self):
        response = self.client.get(reverse("core:home"))
        content = response.content.decode()
        self.assertNotIn("http://", content)
        self.assertNotIn("https://", content)


class HealthViewTests(TestCase):
    def test_health_ok(self):
        response = self.client.get(reverse("core:health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_no_cache(self):
        response = self.client.get(reverse("core:health"))
        self.assertIn("no-cache", response["Cache-Control"])

    def test_health_rejects_post(self):
        response = self.client.post(reverse("core:health"))
        self.assertEqual(response.status_code, 405)

    def test_health_no_db_queries(self):
        with self.assertNumQueries(0):
            self.client.get(reverse("core:health"))
