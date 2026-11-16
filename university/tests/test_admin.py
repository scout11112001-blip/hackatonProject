from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from university.models import Room


class RoomAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")

    def setUp(self):
        self.client.force_login(self.superuser)

    def _post(self, data):
        return self.client.post(reverse("admin:university_room_add"), data)

    def test_valid_room_saved(self):
        response = self._post({"code": "room-201", "floor": "2", "number": "201"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Room.objects.filter(code="room-201").exists())

    def test_bad_number_shows_field_error(self):
        response = self._post({"code": "room-x", "floor": "1", "number": "15"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Номер аудитории", response.content.decode())

    def test_mismatch_shows_error(self):
        response = self._post({"code": "room-y", "floor": "3", "number": "205"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Этаж должен совпадать", response.content.decode())
