from datetime import date, timedelta
from unittest import mock

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from core.testing import FrozenClockMixin, moscow
from notifications.tests.helpers import make_world
from schedule.models import ChangeKind, LessonChange
from schedule.mutations import save_lesson_change
from schedule.tests.helpers import make_lesson, make_room, make_teacher


class ChangedAtTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-11 12:00"

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.room101 = make_room("room-101")
        cls.room102 = make_room("room-102")
        cls.room103 = make_room("room-103")
        cls.teacher = make_teacher("Замена")
        cls.teacher2 = make_teacher("Замена2")
        cls.lesson = make_lesson([cls.w.gx1], weekday=2, slot=1, room=cls.room101)
        cls.lesson2 = make_lesson([cls.w.gx1], weekday=2, slot=2, room=cls.room102)
        cls.T0 = moscow("2026-11-11 12:00")
        cls.T1 = cls.T0 + timedelta(hours=1)

    def _cancel(self):
        return save_lesson_change(
            LessonChange(
                weekly_lesson=self.lesson,
                original_date=date(2026, 11, 11),
                kind=ChangeKind.CANCELLED,
                reason="Причина",
            )
        )

    def _room_change(self):
        return save_lesson_change(
            LessonChange(
                weekly_lesson=self.lesson,
                original_date=date(2026, 11, 11),
                kind=ChangeKind.ROOM_CHANGED,
                new_room=self.room102,
                reason="Причина",
            )
        )

    def _teacher_change(self):
        return save_lesson_change(
            LessonChange(
                weekly_lesson=self.lesson,
                original_date=date(2026, 11, 11),
                kind=ChangeKind.TEACHER_REPLACED,
                new_teacher=self.teacher,
                reason="Причина",
            )
        )

    def _moved_change(self):
        return save_lesson_change(
            LessonChange(
                weekly_lesson=self.lesson,
                original_date=date(2026, 11, 11),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 12),
                new_slot=3,
                reason="Причина",
            )
        )

    def test_insert_sets_changed_at(self):
        change = self._cancel()
        self.assertEqual(change.changed_at, self.T0)
        change2 = LessonChange.objects.create(
            weekly_lesson=self.lesson,
            original_date=date(2026, 11, 18),
            kind=ChangeKind.CANCELLED,
            reason="Причина",
        )
        self.assertEqual(change2.changed_at, self.T0)

    def test_reason_only_keeps_changed_at(self):
        change = self._cancel()
        with mock.patch("django.utils.timezone.now", return_value=self.T1):
            change.reason = "Новая причина"
            save_lesson_change(change)
        change.refresh_from_db()
        self.assertEqual(change.reason, "Новая причина")
        self.assertEqual(change.changed_at, self.T0)

    def test_updated_at_still_moves(self):
        change = self._cancel()
        with mock.patch("django.utils.timezone.now", return_value=self.T1):
            change.reason = "Новая причина"
            save_lesson_change(change)
        change.refresh_from_db()
        self.assertEqual(change.updated_at, self.T1)

    def test_each_visible_field_moves_changed_at(self):
        def original_date(c):
            c.original_date = date(2026, 11, 18)

        def kind(c):
            c.kind = ChangeKind.ROOM_CHANGED
            c.new_room = self.room102

        def new_room(c):
            c.new_room = self.room103

        def new_teacher(c):
            c.new_teacher = self.teacher2

        def new_date(c):
            c.new_date = date(2026, 11, 13)

        def new_slot(c):
            c.new_slot = 4

        def weekly_lesson(c):
            c.weekly_lesson = self.lesson2

        cases = [
            ("original_date", self._cancel, original_date),
            ("kind", self._cancel, kind),
            ("new_room", self._room_change, new_room),
            ("new_teacher", self._teacher_change, new_teacher),
            ("new_date", self._moved_change, new_date),
            ("new_slot", self._moved_change, new_slot),
            ("weekly_lesson", self._cancel, weekly_lesson),
        ]
        for label, setup, mutate in cases:
            with self.subTest(field=label):
                LessonChange.objects.all().delete()
                change = setup()
                self.assertEqual(change.changed_at, self.T0)
                with mock.patch("django.utils.timezone.now", return_value=self.T1):
                    mutate(change)
                    save_lesson_change(change)
                change.refresh_from_db()
                self.assertEqual(change.changed_at, self.T1)

    def test_update_fields_includes_changed_at(self):
        change = self._cancel()
        with mock.patch("django.utils.timezone.now", return_value=self.T1):
            change.original_date = date(2026, 11, 18)
            change.save(update_fields=["original_date"])
        change.refresh_from_db()
        self.assertEqual(change.changed_at, self.T1)

        with mock.patch("django.utils.timezone.now", return_value=self.T1 + timedelta(hours=1)):
            change.reason = "X"
            change.save(update_fields=["reason"])
        change.refresh_from_db()
        self.assertEqual(change.changed_at, self.T1)

    def test_admin_reason_only_keeps_changed_at(self):
        change = self._cancel()
        self.client.force_login(self.w.root)
        with mock.patch("django.utils.timezone.now", return_value=self.T1):
            response = self.client.post(
                reverse("admin:schedule_lessonchange_change", args=[change.pk]),
                {
                    "weekly_lesson": self.lesson.pk,
                    "original_date": "2026-11-11",
                    "kind": "cancelled",
                    "new_date": "",
                    "new_slot": "",
                    "new_room": "",
                    "new_teacher": "",
                    "reason": "Из админки",
                },
            )
        self.assertEqual(response.status_code, 302)
        change.refresh_from_db()
        self.assertEqual(change.reason, "Из админки")
        self.assertEqual(change.changed_at, self.T0)

    def test_admin_visible_edit_moves_changed_at(self):
        change = self._cancel()
        self.client.force_login(self.w.root)
        with mock.patch("django.utils.timezone.now", return_value=self.T1):
            response = self.client.post(
                reverse("admin:schedule_lessonchange_change", args=[change.pk]),
                {
                    "weekly_lesson": self.lesson.pk,
                    "original_date": "2026-11-18",
                    "kind": "cancelled",
                    "new_date": "",
                    "new_slot": "",
                    "new_room": "",
                    "new_teacher": "",
                    "reason": "Причина",
                },
            )
        self.assertEqual(response.status_code, 302)
        change.refresh_from_db()
        self.assertEqual(change.changed_at, self.T1)

    def test_admin_shows_changed_at_readonly(self):
        change = self._cancel()
        self.client.force_login(self.w.root)
        response = self.client.get(reverse("admin:schedule_lessonchange_change", args=[change.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="changed_at"')
        self.assertContains(response, "Изменение для студентов")


class ChangedAtMigrationTests(TransactionTestCase):
    def test_copies_updated_at(self):
        def restore():
            executor = MigrationExecutor(connection)
            executor.loader.build_graph()
            executor.migrate(executor.loader.graph.leaf_nodes())

        self.addCleanup(restore)

        executor = MigrationExecutor(connection)
        executor.migrate([("schedule", "0005_lessonchange_reason_optional")])
        apps = executor.loader.project_state(
            [("schedule", "0005_lessonchange_reason_optional")]
        ).apps

        Room = apps.get_model("university", "Room")
        Teacher = apps.get_model("university", "Teacher")
        Discipline = apps.get_model("university", "Discipline")
        WeeklyLesson = apps.get_model("schedule", "WeeklyLesson")
        LessonChange = apps.get_model("schedule", "LessonChange")

        room = Room.objects.create(code="room-101", floor=1, number="101")
        teacher = Teacher.objects.create(last_name="T", first_name="I")
        discipline = Discipline.objects.create(name="D", short_name="D")
        lesson = WeeklyLesson.objects.create(
            weekday=2,
            slot=1,
            discipline=discipline,
            lesson_type="lecture",
            teacher=teacher,
            room=room,
            valid_from=date(2026, 9, 1),
            valid_until=date(2026, 12, 31),
        )
        c1 = LessonChange.objects.create(
            weekly_lesson=lesson,
            original_date=date(2026, 11, 11),
            kind="cancelled",
            reason="Причина",
        )
        c2 = LessonChange.objects.create(
            weekly_lesson=lesson,
            original_date=date(2026, 11, 18),
            kind="cancelled",
            reason="Причина",
        )
        LessonChange.objects.filter(pk=c1.pk).update(updated_at=moscow("2026-11-10 09:30"))
        LessonChange.objects.filter(pk=c2.pk).update(updated_at=moscow("2026-11-10 15:00"))

        executor2 = MigrationExecutor(connection)
        executor2.migrate([("schedule", "0006_lessonchange_changed_at")])
        apps2 = executor2.loader.project_state([("schedule", "0006_lessonchange_changed_at")]).apps
        LessonChange2 = apps2.get_model("schedule", "LessonChange")

        for pk, expected in (
            (c1.pk, moscow("2026-11-10 09:30")),
            (c2.pk, moscow("2026-11-10 15:00")),
        ):
            row = LessonChange2.objects.get(pk=pk)
            self.assertEqual(row.changed_at, row.updated_at)
            self.assertEqual(row.changed_at, expected)
