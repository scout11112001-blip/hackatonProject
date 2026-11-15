from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from accounts.models import User
from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from university.models import Room


def _svg_part(content: str) -> str:
    start = content.index('<svg class="map-svg"')
    end = content.index("</svg>", start)
    return content[start:end]


class MapAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.student = make_student("stu", cls.group, "REC-1")
        cls.staff = make_staff("stf", cls.faculty)
        cls.superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")
        Room.objects.create(code="room-101", floor=1, number="101", map_cell="N2")
        Room.objects.create(code="room-205", floor=2, number="205", map_cell="N3")

    def test_anonymous_redirected(self):
        for url in ("/map/", "/map/floor/2/", "/map/room/room-205/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith("/login/?next="))

    def test_student_ok(self):
        self.client.force_login(self.student)
        for url in ("/map/", "/map/floor/2/", "/map/room/room-205/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_student_without_profile_ok(self):
        user = User.objects.create_user("noprof", role=User.Role.STUDENT)
        self.client.force_login(user)
        for url in ("/map/", "/map/floor/2/", "/map/room/room-205/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_staff_ok(self):
        self.client.force_login(self.staff)
        for url in ("/map/", "/map/floor/2/", "/map/room/room-205/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_superuser_ok(self):
        self.client.force_login(self.superuser)
        for url in ("/map/", "/map/floor/2/", "/map/room/room-205/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_post_not_allowed(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.post("/map/").status_code, 405)


class MapViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.student = make_student("stu", cls.group, "REC-1")
        Room.objects.create(code="room-101", floor=1, number="101", map_cell="N2")
        Room.objects.create(code="room-114", floor=1, number="114", map_cell="")
        Room.objects.create(code="room-205", floor=2, number="205", map_cell="N3")
        Room.objects.create(code="room-402", floor=4, number="402", map_cell="N3")

    def setUp(self):
        self.client.force_login(self.student)

    def test_default_floor_is_lowest(self):
        content = self.client.get("/map/").content.decode()
        self.assertIn('<title id="map-title">Схема, 1 этаж</title>', content)

    def test_switcher_lists_only_floors_with_rooms(self):
        content = self.client.get("/map/").content.decode()
        self.assertIn('href="/map/floor/1/"', content)
        self.assertIn('href="/map/floor/2/"', content)
        self.assertIn('href="/map/floor/4/"', content)
        self.assertNotIn('href="/map/floor/3/"', content)

    def test_current_floor_marked(self):
        content = self.client.get("/map/floor/2/").content.decode()
        self.assertEqual(content.count('aria-current="page"'), 1)
        self.assertIn('href="/map/floor/2/" class="floor-current" aria-current="page"', content)

    def test_floor_without_rooms_404(self):
        for url in ("/map/floor/3/", "/map/floor/0/", "/map/floor/10/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_non_numeric_floor_404(self):
        for url in ("/map/floor/abc/", "/map/floor/-1/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_room_opens_its_floor_and_is_highlighted(self):
        content = self.client.get("/map/room/room-402/").content.decode()
        self.assertIn('<title id="map-title">Схема, 4 этаж</title>', content)
        self.assertEqual(_svg_part(content).count("map-current"), 1)
        self.assertIn('href="/map/room/room-402/" class="map-current"', content)
        self.assertEqual(content.count("map-current"), 2)

    def test_highlight_has_accessible_name(self):
        content = self.client.get("/map/room/room-402/").content.decode()
        self.assertIn('aria-current="location"', _svg_part(content))
        self.assertIn("<title>Аудитория 402</title>", content)

    def test_unknown_room_404(self):
        for url in ("/map/room/room-404/", "/map/room/ROOM-101/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_room_without_cell_listed_and_floor_opens(self):
        content = self.client.get("/map/room/room-114/").content.decode()
        self.assertIn("114</a> — нет на схеме", content)
        self.assertIn('<title id="map-title">Схема, 1 этаж</title>', content)
        self.assertNotIn("map-current", _svg_part(content))
        self.assertIn('href="/map/room/room-114/" class="map-current"', content)

    def test_landmarks_per_floor(self):
        f1 = _svg_part(self.client.get("/map/floor/1/").content.decode())
        for label in ("Вход", "Столовая", "Лестница"):
            self.assertIn(label, f1)
        for label in ("Деканат", "Библиотека"):
            self.assertNotIn(label, f1)
        f2 = _svg_part(self.client.get("/map/floor/2/").content.decode())
        self.assertIn("Деканат", f2)
        for label in ("Вход", "Столовая", "Библиотека"):
            self.assertNotIn(label, f2)
        f4 = _svg_part(self.client.get("/map/floor/4/").content.decode())
        self.assertIn("Лестница", f4)
        for label in ("Вход", "Столовая", "Деканат", "Библиотека"):
            self.assertNotIn(label, f4)

    def test_legend_present(self):
        content = self.client.get("/map/").content.decode()
        self.assertIn("map-legend", content)
        self.assertIn("Аудитория", content)

    def test_room_list_grouped_by_floor(self):
        content = self.client.get("/map/").content.decode()
        for heading in ("<h3>1 этаж</h3>", "<h3>2 этаж</h3>", "<h3>4 этаж</h3>"):
            self.assertIn(heading, content)
        for code in ("room-101", "room-114", "room-205", "room-402"):
            self.assertIn(f'href="/map/room/{code}/"', content)

    def test_no_rooms_empty_state(self):
        Room.objects.all().delete()
        content = self.client.get("/map/").content.decode()
        self.assertIn("Аудиторий пока нет.", content)

    def test_query_string_not_rendered(self):
        content = self.client.get("/map/?floor=<script>x</script>&room=room-205").content.decode()
        self.assertIn('<title id="map-title">Схема, 1 этаж</title>', content)
        self.assertNotIn("<script>x</script>", content)
        self.assertNotIn('aria-current="location"', content)

    def test_svg_scales(self):
        content = self.client.get("/map/").content.decode()
        self.assertIn('viewBox="0 0 400 240"', content)
        svg_tag = content[
            content.index('<svg class="map-svg"') : content.index(
                ">", content.index('<svg class="map-svg"')
            )
        ]
        self.assertNotIn(" width=", svg_tag)
        self.assertNotIn(" height=", svg_tag)

    def test_no_personal_data(self):
        student = make_student("personal", self.group, "REC-P")
        self.client.force_login(student)
        content = self.client.get("/map/").content.decode()
        self.assertNotIn("personal", content)
        self.assertNotIn("personal-last", content)


class MapQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.staff = make_staff("stf", cls.faculty)
        Room.objects.create(code="room-101", floor=1, number="101", map_cell="N2")
        Room.objects.create(code="room-114", floor=1, number="114", map_cell="")
        Room.objects.create(code="room-205", floor=2, number="205", map_cell="N3")
        Room.objects.create(code="room-402", floor=4, number="402", map_cell="N3")

    def _add_many_rooms(self):
        used = {r.number for r in Room.objects.all()}
        for floor in range(1, 10):
            for n in range(0, 10):
                number = f"{floor}0{n}"
                if number not in used:
                    used.add(number)
                    Room.objects.create(code=f"room-{number}", floor=floor, number=number)
                    if len(used) >= 20:
                        return

    def _count(self, url):
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(url)
        return len(ctx.captured_queries)

    def test_queries_constant(self):
        self.client.force_login(self.staff)
        count4 = self._count("/map/")
        self._add_many_rooms()
        count20 = self._count("/map/")
        self.assertEqual(count4, count20)
        self.assertLessEqual(count4, 4)

    def test_highlight_view_same_queries(self):
        self.client.force_login(self.staff)
        self.assertEqual(self._count("/map/room/room-205/"), self._count("/map/"))


class MapNavTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.student = make_student("stu", cls.group, "REC-1")
        cls.staff = make_staff("stf", cls.faculty)
        cls.superuser = User.objects.create_superuser("root", password="Super-Pass-2026!")

    def test_student_nav_has_map(self):
        self.client.force_login(self.student)
        content = self.client.get("/profile/").content.decode()
        self.assertIn('href="/map/"', content)

    def test_staff_nav_has_map(self):
        self.client.force_login(self.staff)
        content = self.client.get("/profile/").content.decode()
        self.assertIn('href="/map/"', content)

    def test_superuser_nav_has_no_map(self):
        self.client.force_login(self.superuser)
        content = self.client.get("/profile/").content.decode()
        self.assertNotIn('href="/map/"', content)
