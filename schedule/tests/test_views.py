from datetime import date
from unittest import mock

from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from accounts.tests.helpers import make_faculty, make_group, make_staff, make_student
from core.testing import FrozenClockMixin
from schedule.converters import IsoDateConverter
from schedule.models import ChangeKind, LessonChange
from schedule.mutations import save_lesson_change
from university.models import Teacher

from .helpers import aware, make_discipline, make_lesson, make_room, make_teacher


class IsoDateConverterTests(SimpleTestCase):
    def test_to_python(self):
        conv = IsoDateConverter()
        self.assertEqual(conv.to_python("2026-11-16"), date(2026, 11, 16))

    def test_to_python_invalid(self):
        conv = IsoDateConverter()
        for value in ("2026-02-30", "1999-12-31"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    conv.to_python(value)

    def test_to_url(self):
        conv = IsoDateConverter()
        self.assertEqual(conv.to_url(date(2026, 11, 16)), "2026-11-16")


class ScheduleViewsTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty_x = make_faculty("FX")
        cls.faculty_y = make_faculty("FY")
        cls.group_x1 = make_group(cls.faculty_x, "GX1")
        cls.group_x2 = make_group(cls.faculty_x, "GX2")
        cls.group_y = make_group(cls.faculty_y, "GY")
        cls.student_a = make_student("a", cls.group_x1, "REC-A")
        cls.student_b = make_student("b", cls.group_y, "REC-B")
        cls.staff_x = make_staff("sx", cls.faculty_x)
        cls.staff_y = make_staff("sy", cls.faculty_y)
        cls.room = make_room("room-101")
        cls.teacher = make_teacher("Лебедев")
        cls.d1 = make_discipline("GX1-дисциплина-1")
        cls.d2 = make_discipline("GX1-дисциплина-2")
        cls.d3 = make_discipline("GX1-дисциплина-3")
        cls.d_gy = make_discipline("GY-дисциплина")
        cls.d_shared = make_discipline("Общая дисциплина")
        make_lesson([cls.group_x1], 0, 1, cls.room, discipline=cls.d1, teacher=cls.teacher)
        make_lesson([cls.group_x1], 0, 2, cls.room, discipline=cls.d2, teacher=cls.teacher)
        make_lesson([cls.group_x1], 0, 3, cls.room, discipline=cls.d3, teacher=cls.teacher)
        make_lesson([cls.group_y], 0, 4, cls.room, discipline=cls.d_gy, teacher=cls.teacher)
        make_lesson(
            [cls.group_x1, cls.group_y],
            1,
            1,
            cls.room,
            discipline=cls.d_shared,
            teacher=cls.teacher,
        )
        # A base change so both query-count measurements have a non-empty change list.
        wed_lesson = make_lesson(
            [cls.group_x1],
            2,
            1,
            cls.room,
            discipline=make_discipline("Средовая дисциплина"),
            teacher=cls.teacher,
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=wed_lesson,
                original_date=date(2026, 11, 18),
                kind=ChangeKind.CANCELLED,
                reason="Отмена",
            )
        )

    def test_anonymous_redirected(self):
        urls = [
            "/schedule/",
            "/schedule/week/",
            "/schedule/week/2026-11-16/",
            "/staff/schedule/",
            f"/staff/schedule/{self.group_x1.pk}/",
            f"/staff/schedule/{self.group_x1.pk}/2026-11-16/",
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith("/login/?next="))

    def test_student_urls_have_no_ids(self):
        self.assertEqual(reverse("schedule:today"), "/schedule/")
        self.assertEqual(reverse("schedule:week"), "/schedule/week/")

    def test_today_in_progress_and_next(self):
        self.client.force_login(self.student_a)
        with mock.patch("django.utils.timezone.now", return_value=aware("2026-11-16 10:50")):
            response = self.client.get("/schedule/")
        annotation = response.context["annotation"]
        self.assertEqual(annotation.in_progress.slot.number, 2)
        self.assertEqual(annotation.next_item.slot.number, 3)
        content = response.content.decode()
        self.assertIn("Сейчас", content)
        self.assertIn("Следующая", content)

    def test_today_empty_day(self):
        self.client.force_login(self.student_a)
        with mock.patch("django.utils.timezone.now", return_value=aware("2026-11-22 12:00")):
            response = self.client.get("/schedule/")
        self.assertIn("Сегодня занятий нет.", response.content.decode())

    def test_today_day_finished(self):
        self.client.force_login(self.student_a)
        with mock.patch("django.utils.timezone.now", return_value=aware("2026-11-16 22:00")):
            response = self.client.get("/schedule/")
        self.assertIn("Занятия на сегодня закончились.", response.content.decode())

    def test_week_shows_only_own_group(self):
        self.client.force_login(self.student_a)
        content = self.client.get("/schedule/week/").content.decode()
        self.assertIn(self.d1.name, content)
        self.assertIn(self.d2.name, content)
        self.assertIn(self.d3.name, content)
        self.assertIn(self.d_shared.name, content)
        self.assertNotIn(self.d_gy.name, content)

    def test_week_navigation(self):
        self.client.force_login(self.student_a)
        response = self.client.get("/schedule/week/2026-11-18/")
        self.assertEqual(response.context["week"].start, date(2026, 11, 16))
        content = response.content.decode()
        self.assertIn("/schedule/week/2026-11-09/", content)
        self.assertIn("/schedule/week/2026-11-23/", content)

    def test_week_boundaries(self):
        sunday_disc = make_discipline("Воскресная дисциплина")
        make_lesson([self.group_x1], 6, 1, self.room, discipline=sunday_disc, teacher=self.teacher)
        self.client.force_login(self.student_a)
        response = self.client.get("/schedule/week/2026-11-16/")
        week = response.context["week"]
        self.assertEqual(week.start, date(2026, 11, 16))
        self.assertEqual(week.end, date(2026, 11, 22))
        self.assertEqual(week.days[-1].date, date(2026, 11, 22))
        self.assertTrue(
            any(i.lesson.discipline.name == "Воскресная дисциплина" for i in week.days[6].items)
        )

    def test_invalid_date_404(self):
        self.client.force_login(self.student_a)
        self.assertEqual(self.client.get("/schedule/week/2026-02-30/").status_code, 404)
        self.assertEqual(self.client.get("/schedule/week/1999-12-31/").status_code, 404)

    def test_room_code_attribute(self):
        self.client.force_login(self.student_a)
        content = self.client.get("/schedule/week/2026-11-16/").content.decode()
        self.assertIn('data-room-code="room-101"', content)

    def test_student_forbidden_on_staff_pages(self):
        self.client.force_login(self.student_a)
        for url in [
            "/staff/schedule/",
            f"/staff/schedule/{self.group_x1.pk}/",
            f"/staff/schedule/{self.group_x1.pk}/2026-11-16/",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_staff_group_list_scoped(self):
        self.client.force_login(self.staff_x)
        content = self.client.get("/staff/schedule/").content.decode()
        self.assertIn("GX1", content)
        self.assertIn("GX2", content)
        self.assertNotIn("GY", content)

    def test_staff_group_week_own_faculty(self):
        self.client.force_login(self.staff_x)
        response = self.client.get(f"/staff/schedule/{self.group_x1.pk}/2026-11-16/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.d1.name, response.content.decode())

    def test_staff_other_faculty_group_404(self):
        self.client.force_login(self.staff_x)
        self.assertEqual(self.client.get(f"/staff/schedule/{self.group_y.pk}/").status_code, 404)
        self.assertEqual(self.client.get("/staff/schedule/999999/").status_code, 404)

    def test_nav_schedule_link(self):
        self.client.force_login(self.student_a)
        content_a = self.client.get("/profile/").content.decode()
        self.assertIn("/schedule/", content_a)
        self.client.force_login(self.staff_x)
        content_x = self.client.get("/profile/").content.decode()
        self.assertIn("/staff/schedule/", content_x)

    def test_week_view_query_count_constant(self):
        self.client.force_login(self.student_a)
        self.client.get("/schedule/week/2026-11-16/")
        with CaptureQueriesContext(connection) as ctx:
            self.client.get("/schedule/week/2026-11-16/")
        count1 = len(ctx.captured_queries)

        room2 = make_room("room-999", floor=9)
        lessons = []
        for n in range(10):
            lessons.append(
                make_lesson(
                    [self.group_x1],
                    weekday=n % 5,
                    slot=5 + (n % 3),
                    room=room2,
                    discipline=make_discipline(f"Дополнительная {n}"),
                    teacher=self.teacher,
                )
            )
        for n in range(5):
            lesson = lessons[n]
            original = date(2026, 11, 16) if lesson.weekday == 0 else None
            for d in (16, 17, 18, 19, 20, 21, 22):
                if date(2026, 11, d).weekday() == lesson.weekday:
                    original = date(2026, 11, d)
                    break
            save_lesson_change(
                LessonChange(
                    weekly_lesson=lesson,
                    original_date=original,
                    kind=ChangeKind.CANCELLED,
                    reason="Отмена",
                )
            )
        with CaptureQueriesContext(connection) as ctx2:
            self.client.get("/schedule/week/2026-11-16/")
        count2 = len(ctx2.captured_queries)
        self.assertEqual(count2, count1)


class ChangeRenderingTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.student = make_student("a", cls.group, "REC-A")
        cls.room = make_room("room-101")
        cls.room2 = make_room("room-205", floor=2)
        cls.teacher = make_teacher("Лебедев")
        cls.teacher2 = make_teacher("Воронцова")
        cls.disc = make_discipline("Математика")

        cls.lesson_cancel = make_lesson(
            [cls.group],
            0,
            1,
            cls.room,
            discipline=make_discipline("Отменённая"),
            teacher=cls.teacher,
        )
        cls.lesson_move = make_lesson(
            [cls.group],
            1,
            1,
            cls.room,
            discipline=make_discipline("Перенесённая"),
            teacher=cls.teacher,
        )
        cls.lesson_room = make_lesson(
            [cls.group],
            2,
            1,
            cls.room,
            discipline=make_discipline("С заменой аудитории"),
            teacher=cls.teacher,
        )
        cls.lesson_teacher = make_lesson(
            [cls.group],
            3,
            1,
            cls.room,
            discipline=make_discipline("С заменой преподавателя"),
            teacher=cls.teacher,
        )

        save_lesson_change(
            LessonChange(
                weekly_lesson=cls.lesson_cancel,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="Преподаватель на конференции",
            )
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=cls.lesson_move,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 19),
                new_slot=5,
                reason="Перенос по просьбе",
            )
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=cls.lesson_room,
                original_date=date(2026, 11, 18),
                kind=ChangeKind.ROOM_CHANGED,
                new_room=cls.room2,
                reason="Ремонт в аудитории",
            )
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=cls.lesson_teacher,
                original_date=date(2026, 11, 19),
                kind=ChangeKind.TEACHER_REPLACED,
                new_teacher=cls.teacher2,
                reason="Болезнь преподавателя",
            )
        )

    def test_change_rendering(self):
        self.client.force_login(self.student)
        content = self.client.get("/schedule/week/2026-11-16/").content.decode()
        self.assertIn("Отменено", content)
        self.assertIn("Перенесено на", content)
        self.assertIn("Перенесено с", content)
        self.assertIn("Замена аудитории", content)
        self.assertIn("Замена преподавателя", content)
        for reason in (
            "Преподаватель на конференции",
            "Перенос по просьбе",
            "Ремонт в аудитории",
            "Болезнь преподавателя",
        ):
            self.assertIn(reason, content)
        self.assertIn("<del", content)
        self.assertIn("<ins", content)
        self.assertIn("205", content)  # new room number
        self.assertIn("101", content)  # old room number
        self.assertIn("Лебедев", content)
        self.assertIn("Воронцова", content)


class ScheduleUiFixTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FU")
        cls.group = make_group(cls.faculty, "GU")
        cls.student = make_student("su", cls.group, "REC-U")
        cls.room = make_room("room-101")
        cls.room2 = make_room("room-205", floor=2)
        cls.teacher = make_teacher("Лебедев")
        cls.teacher2 = make_teacher("Воронцова")
        cls.lesson_cancel = make_lesson(
            [cls.group], 0, 1, cls.room, discipline=make_discipline("Отмен"), teacher=cls.teacher
        )
        cls.lesson_move = make_lesson(
            [cls.group], 1, 1, cls.room, discipline=make_discipline("Перенос"), teacher=cls.teacher
        )
        cls.lesson_room = make_lesson(
            [cls.group], 2, 1, cls.room, discipline=make_discipline("Ауд"), teacher=cls.teacher
        )
        cls.lesson_teacher = make_lesson(
            [cls.group], 3, 1, cls.room, discipline=make_discipline("Преп"), teacher=cls.teacher
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=cls.lesson_cancel,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="Отмена",
            )
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=cls.lesson_move,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 19),
                new_slot=5,
                reason="Перенос",
            )
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=cls.lesson_room,
                original_date=date(2026, 11, 18),
                kind=ChangeKind.ROOM_CHANGED,
                new_room=cls.room2,
                reason="Ремонт",
            )
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=cls.lesson_teacher,
                original_date=date(2026, 11, 19),
                kind=ChangeKind.TEACHER_REPLACED,
                new_teacher=cls.teacher2,
                reason="Болезнь",
            )
        )

    def test_student_week_has_no_back_link(self):
        self.client.force_login(self.student)
        content = self.client.get("/schedule/week/2026-11-16/").content.decode()
        self.assertNotIn("К списку групп", content)

    def test_staff_week_back_link_url(self):
        staff = make_staff("sfu", self.faculty)
        self.client.force_login(staff)
        content = self.client.get(f"/staff/schedule/{self.group.pk}/2026-11-16/").content.decode()
        self.assertIn('href="/staff/schedule/"', content)
        self.assertIn("К списку групп", content)

    def test_change_label_no_space_before_period(self):
        self.client.force_login(self.student)
        content = self.client.get("/schedule/week/2026-11-16/").content.decode()
        self.assertIn("Отменено. Причина:", content)
        self.assertIn("Замена аудитории. Причина:", content)
        self.assertIn("Замена преподавателя. Причина:", content)
        self.assertIn("). Причина:", content)  # moved-out
        self.assertIn("пара. Причина:", content)  # moved-in
        self.assertNotIn(" . Причина", content)


class TeacherShortNameRenderTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-11 12:00"

    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX1")
        cls.student = make_student("a", cls.group, "REC-A")
        cls.room = make_room("room-101")
        cls.teacher = Teacher.objects.create(
            last_name="Шестакова", first_name="Людмила", middle_name="Петровна"
        )
        make_lesson(
            [cls.group],
            2,
            1,
            cls.room,
            discipline=make_discipline("Дисциплина"),
            teacher=cls.teacher,
        )

    def test_week_page_has_no_break_spaces(self):
        self.client.force_login(self.student)
        content = self.client.get(
            reverse("schedule:week_of", kwargs={"day": date(2026, 11, 11)})
        ).content.decode()
        self.assertIn("Шестакова\u00a0Л.\u00a0П.", content)
        self.assertNotIn("Шестакова Л.", content)


class RoomLinkTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.student = make_student("stu", cls.group, "REC-1")
        cls.staff = make_staff("stf", cls.faculty)
        cls.teacher = make_teacher("Лебедев")

        cls.room = make_room("room-101")
        cls.room_cancel = make_room("room-202")
        cls.room_move = make_room("room-303")
        cls.room_changed_old = make_room("room-404")
        cls.room_changed_new = make_room("room-205", floor=2)
        cls.room_move_in_old = make_room("room-505")
        cls.room_move_in_new = make_room("room-206", floor=2)

        cls.lesson_regular = make_lesson(
            [cls.group],
            0,
            1,
            cls.room,
            discipline=make_discipline("Регулярная"),
            teacher=cls.teacher,
        )
        cls.lesson_cancel = make_lesson(
            [cls.group],
            1,
            1,
            cls.room_cancel,
            discipline=make_discipline("Отменённая"),
            teacher=cls.teacher,
        )
        cls.lesson_move = make_lesson(
            [cls.group],
            2,
            1,
            cls.room_move,
            discipline=make_discipline("Перенесённая"),
            teacher=cls.teacher,
        )
        cls.lesson_changed = make_lesson(
            [cls.group],
            3,
            1,
            cls.room_changed_old,
            discipline=make_discipline("С заменой"),
            teacher=cls.teacher,
        )
        cls.lesson_move_in = make_lesson(
            [cls.group],
            0,
            2,
            cls.room_move_in_old,
            discipline=make_discipline("Въехавшая"),
            teacher=cls.teacher,
        )
        cls.lesson_today = make_lesson(
            [cls.group],
            2,
            2,
            cls.room,
            discipline=make_discipline("Сегодняшняя"),
            teacher=cls.teacher,
        )

        save_lesson_change(
            LessonChange(
                weekly_lesson=cls.lesson_cancel,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.CANCELLED,
                reason="Отмена",
            )
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=cls.lesson_move,
                original_date=date(2026, 11, 18),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 28),
                new_slot=5,
                reason="Перенос",
            )
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=cls.lesson_changed,
                original_date=date(2026, 11, 19),
                kind=ChangeKind.ROOM_CHANGED,
                new_room=cls.room_changed_new,
                reason="Ремонт",
            )
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=cls.lesson_move_in,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 20),
                new_slot=5,
                new_room=cls.room_move_in_new,
                reason="Перенос",
            )
        )

    def _week(self):
        self.client.force_login(self.student)
        return self.client.get("/schedule/week/2026-11-16/").content.decode()

    def test_regular_lesson_room_links_to_map(self):
        content = self._week()
        self.assertIn('href="/map/room/room-101/"', content)
        self.assertIn('data-room-code="room-101"', content)

    def test_cancelled_lesson_room_not_linked(self):
        content = self._week()
        self.assertIn('<span class="room" data-room-code="room-202">202, 2 этаж</span>', content)
        self.assertNotIn('href="/map/room/room-202/"', content)

    def test_moved_out_lesson_room_not_linked(self):
        content = self._week()
        self.assertIn('<span class="room" data-room-code="room-303">303, 3 этаж</span>', content)
        self.assertNotIn('href="/map/room/room-303/"', content)

    def test_room_changed_links_new_room_only(self):
        content = self._week()
        self.assertIn('href="/map/room/room-205/"', content)
        self.assertIn('<del class="room" data-room-code="room-404">404, 4 этаж</del>', content)
        self.assertNotIn('href="/map/room/room-404/"', content)

    def test_moved_in_with_new_room_links_new_room(self):
        content = self._week()
        self.assertIn('href="/map/room/room-206/"', content)
        self.assertNotIn('href="/map/room/room-505/"', content)

    def test_today_page_has_links(self):
        self.client.force_login(self.student)
        content = self.client.get("/schedule/").content.decode()
        self.assertIn('href="/map/room/room-101/"', content)

    def test_staff_group_week_has_links(self):
        self.client.force_login(self.staff)
        content = self.client.get(f"/staff/schedule/{self.group.pk}/2026-11-16/").content.decode()
        self.assertIn('href="/map/room/room-101/"', content)

    def test_week_query_count_unchanged_by_links(self):
        self.client.force_login(self.student)
        with CaptureQueriesContext(connection) as ctx:
            self.client.get("/schedule/week/2026-11-16/")
        count1 = len(ctx.captured_queries)
        for n in range(5):
            make_lesson(
                [self.group],
                weekday=6,
                slot=n + 2,
                room=self.room,
                discipline=make_discipline(f"Доп {n}"),
                teacher=self.teacher,
            )
        with CaptureQueriesContext(connection) as ctx2:
            self.client.get("/schedule/week/2026-11-16/")
        count2 = len(ctx2.captured_queries)
        self.assertEqual(count2, count1)
