from datetime import UTC, date, datetime, time

from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext

from accounts.tests.helpers import make_faculty, make_group
from core.testing import FrozenClockMixin, moscow
from schedule.models import ChangeKind, LessonChange
from schedule.mutations import save_lesson_change
from schedule.services import (
    ItemKind,
    annotate_today,
    changes_for_groups_between,
    day_schedule,
    occurrences_between,
    today_schedule,
    week_schedule,
    week_start,
)

from .helpers import make_lesson, make_room, make_teacher


class WeekStartTests(SimpleTestCase):
    def test_week_start(self):
        self.assertEqual(week_start(date(2026, 11, 16)), date(2026, 11, 16))
        self.assertEqual(week_start(date(2026, 11, 22)), date(2026, 11, 16))
        self.assertEqual(week_start(date(2026, 11, 18)), date(2026, 11, 16))


class OccurrencesTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group_a = make_group(cls.faculty, "GA")
        cls.group_b = make_group(cls.faculty, "GB")
        cls.room = make_room("room-101")
        cls.room2 = make_room("room-205", floor=2)
        cls.teacher = make_teacher("Лебедев")
        cls.teacher2 = make_teacher("Воронцова")

    def test_weekday_and_validity_bounds(self):
        make_lesson(
            [self.group_a],
            weekday=0,
            slot=1,
            room=self.room,
            valid_from=date(2026, 11, 16),
            valid_until=date(2026, 11, 23),
        )
        items = occurrences_between(date(2026, 11, 16), date(2026, 11, 23), [self.group_a.id])
        self.assertEqual([i.date for i in items], [date(2026, 11, 16), date(2026, 11, 23)])
        self.assertEqual(
            occurrences_between(date(2026, 11, 9), date(2026, 11, 9), [self.group_a.id]), []
        )
        self.assertEqual(
            occurrences_between(date(2026, 11, 30), date(2026, 11, 30), [self.group_a.id]), []
        )

    def test_shared_lecture_visible_to_both_groups(self):
        make_lesson([self.group_a, self.group_b], weekday=0, slot=1, room=self.room)
        for gid in (self.group_a.id, self.group_b.id):
            items = occurrences_between(date(2026, 11, 16), date(2026, 11, 16), [gid])
            self.assertEqual(len(items), 1)

    def test_group_isolation(self):
        make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        items = occurrences_between(date(2026, 11, 16), date(2026, 11, 16), [self.group_b.id])
        self.assertEqual(items, [])

    def test_cancelled_item(self):
        lesson = make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="Отменено",
            )
        )
        items = occurrences_between(date(2026, 11, 16), date(2026, 11, 16), [self.group_a.id])
        self.assertEqual(items[0].kind, ItemKind.CANCELLED)

    def test_room_changed_item(self):
        lesson = make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.ROOM_CHANGED,
                new_room=self.room2,
                reason="Ремонт",
            )
        )
        items = occurrences_between(date(2026, 11, 16), date(2026, 11, 16), [self.group_a.id])
        item = items[0]
        self.assertEqual(item.kind, ItemKind.ROOM_CHANGED)
        self.assertEqual(item.room, self.room2)
        self.assertEqual(item.original_room, self.room)

    def test_teacher_replaced_item(self):
        lesson = make_lesson(
            [self.group_a], weekday=0, slot=1, room=self.room, teacher=self.teacher
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.TEACHER_REPLACED,
                new_teacher=self.teacher2,
                reason="Болезнь",
            )
        )
        items = occurrences_between(date(2026, 11, 16), date(2026, 11, 16), [self.group_a.id])
        item = items[0]
        self.assertEqual(item.kind, ItemKind.TEACHER_REPLACED)
        self.assertEqual(item.teacher, self.teacher2)
        self.assertEqual(item.original_teacher, self.teacher)

    def test_move_within_week(self):
        lesson = make_lesson([self.group_a], weekday=1, slot=1, room=self.room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 17),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 19),
                new_slot=5,
                reason="Перенос",
            )
        )
        week = week_schedule(date(2026, 11, 18), [self.group_a.id], today=date(2026, 11, 18))
        kinds = [i.kind for d in week.days for i in d.items]
        self.assertIn(ItemKind.MOVED_OUT, kinds)
        self.assertIn(ItemKind.MOVED_IN, kinds)

    def test_move_across_week(self):
        lesson = make_lesson(
            [self.group_a],
            weekday=0,
            slot=1,
            room=self.room,
            valid_from=date(2026, 11, 16),
            valid_until=date(2026, 11, 16),
        )
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 24),
                new_slot=4,
                reason="Перенос",
            )
        )
        week1 = week_schedule(date(2026, 11, 16), [self.group_a.id], today=date(2026, 11, 16))
        kinds1 = [i.kind for d in week1.days for i in d.items]
        self.assertIn(ItemKind.MOVED_OUT, kinds1)
        self.assertNotIn(ItemKind.MOVED_IN, kinds1)
        week2 = week_schedule(date(2026, 11, 23), [self.group_a.id], today=date(2026, 11, 23))
        kinds2 = [i.kind for d in week2.days for i in d.items]
        self.assertIn(ItemKind.MOVED_IN, kinds2)
        self.assertNotIn(ItemKind.MOVED_OUT, kinds2)
        day = day_schedule(date(2026, 11, 24), [self.group_a.id], today=date(2026, 11, 24))
        self.assertEqual(day.items[0].kind, ItemKind.MOVED_IN)

    def test_move_within_same_day(self):
        lesson = make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 16),
                new_slot=5,
                reason="Перенос",
            )
        )
        items = occurrences_between(date(2026, 11, 16), date(2026, 11, 16), [self.group_a.id])
        kinds = [i.kind for i in items]
        self.assertIn(ItemKind.MOVED_OUT, kinds)
        self.assertIn(ItemKind.MOVED_IN, kinds)
        self.assertEqual(items[0].slot.number, 1)
        self.assertEqual(items[-1].slot.number, 5)

    def test_move_with_new_room(self):
        lesson = make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 19),
                new_slot=5,
                new_room=self.room2,
                reason="Перенос",
            )
        )
        day = day_schedule(date(2026, 11, 19), [self.group_a.id], today=date(2026, 11, 19))
        item = day.items[0]
        self.assertEqual(item.room, self.room2)
        self.assertEqual(item.original_room, self.room)

    def test_week_has_seven_days_and_today_flag(self):
        make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        week = week_schedule(date(2026, 11, 18), [self.group_a.id], today=date(2026, 11, 18))
        self.assertEqual(len(week.days), 7)
        self.assertEqual(week.start, date(2026, 11, 16))
        self.assertEqual(week.end, date(2026, 11, 22))
        self.assertTrue(week.days[2].is_today)

    def test_changes_for_groups_between(self):
        lesson_a = make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        lesson_b = make_lesson([self.group_b], weekday=0, slot=2, room=self.room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson_a,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="Отмена",
            )
        )
        moved = save_lesson_change(
            LessonChange(
                weekly_lesson=lesson_b,
                original_date=date(2026, 11, 9),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 18),
                new_slot=5,
                reason="Перенос",
            )
        )
        qs = changes_for_groups_between([self.group_a.id], date(2026, 11, 16), date(2026, 11, 22))
        self.assertEqual(set(qs.values_list("id", flat=True)), {lesson_a.changes.first().id})
        qs_b = changes_for_groups_between([self.group_b.id], date(2026, 11, 16), date(2026, 11, 22))
        self.assertEqual(set(qs_b.values_list("id", flat=True)), {moved.id})
        qs_all = changes_for_groups_between(None, date(2026, 11, 16), date(2026, 11, 22))
        self.assertEqual(qs_all.count(), 2)

    def test_query_count_constant(self):
        make_lesson([self.group_a], weekday=0, slot=1, room=self.room)
        lesson = make_lesson([self.group_a], weekday=0, slot=2, room=self.room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="Отмена",
            )
        )
        with CaptureQueriesContext(connection) as ctx:
            week_schedule(date(2026, 11, 18), [self.group_a.id], today=date(2026, 11, 18))
        count1 = len(ctx.captured_queries)

        for n in range(10):
            make_lesson([self.group_a], weekday=(n % 5), slot=3 + (n % 3), room=self.room)
        for n in range(5):
            extra_lesson = make_lesson([self.group_a], weekday=6, slot=1 + n, room=self.room)
            save_lesson_change(
                LessonChange(
                    weekly_lesson=extra_lesson,
                    original_date=date(2026, 11, 22),
                    kind=ChangeKind.CANCELLED,
                    reason="Отмена",
                )
            )
        with CaptureQueriesContext(connection) as ctx2:
            week_schedule(date(2026, 11, 18), [self.group_a.id], today=date(2026, 11, 18))
        count2 = len(ctx2.captured_queries)
        self.assertEqual(count2, count1)
        self.assertLessEqual(count1, 4)


class AnnotateTodayTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FA")
        cls.group = make_group(cls.faculty, "GA")
        cls.room = make_room("room-101")
        cls.lessons = {
            slot: make_lesson([cls.group], weekday=0, slot=slot, room=cls.room)
            for slot in (1, 2, 3, 4)
        }

    def _items(self):
        return occurrences_between(date(2026, 11, 16), date(2026, 11, 16), [self.group.id])

    def test_before_first_lesson(self):
        a = annotate_today(self._items(), time(8, 0))
        self.assertIsNone(a.in_progress)
        self.assertEqual(a.next_item.slot.number, 1)
        self.assertFalse(a.day_finished)

    def test_during_slot_2(self):
        a = annotate_today(self._items(), time(10, 50))
        self.assertEqual(a.in_progress.slot.number, 2)
        self.assertEqual(a.next_item.slot.number, 3)

    def test_break_between_slots(self):
        a = annotate_today(self._items(), time(12, 30))
        self.assertIsNone(a.in_progress)
        self.assertEqual(a.next_item.slot.number, 3)

    def test_exactly_at_end_of_slot(self):
        a = annotate_today(self._items(), time(12, 10))
        self.assertIsNone(a.in_progress)

    def test_after_last_lesson(self):
        a = annotate_today(self._items(), time(18, 0))
        self.assertIsNone(a.in_progress)
        self.assertIsNone(a.next_item)
        self.assertTrue(a.day_finished)

    def test_cancelled_slot_skipped(self):
        save_lesson_change(
            LessonChange(
                weekly_lesson=self.lessons[3],
                original_date=date(2026, 11, 16),
                kind=ChangeKind.CANCELLED,
                reason="Отмена",
            )
        )
        a = annotate_today(self._items(), time(11, 0))
        self.assertEqual(a.next_item.slot.number, 4)

    def test_empty_list(self):
        a = annotate_today([], time(10, 0))
        self.assertIsNone(a.in_progress)
        self.assertIsNone(a.next_item)
        self.assertFalse(a.day_finished)
        self.assertEqual(a.rows, [])


class TodayScheduleTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-11 11:00"

    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FT")
        cls.group = make_group(cls.faculty, "GT")
        cls.room = make_room("room-101")
        for slot in (1, 2, 3):
            make_lesson([cls.group], weekday=2, slot=slot, room=cls.room)

    def test_matches_today_view_logic(self):
        day, annotation = today_schedule(self.group.pk, moscow("2026-11-11 11:00"))
        self.assertEqual(day.date, date(2026, 11, 11))
        self.assertTrue(day.is_today)
        self.assertEqual(annotation.in_progress.slot.number, 2)
        self.assertEqual(len(annotation.rows), 3)

    def test_uses_moscow_local_date(self):
        day, _ = today_schedule(self.group.pk, datetime(2026, 11, 17, 21, 0, tzinfo=UTC))
        self.assertEqual(day.date, date(2026, 11, 18))
