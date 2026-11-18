from datetime import date, timedelta
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from academics.models import CurrentMark, FinalResult
from academics.tests.helpers import make_item, make_mark, make_result, make_term
from core.testing import FrozenClockMixin, moscow
from notifications.feed import (
    badge_for_user,
    badge_label,
    build_feed,
    home_summary,
    student_context,
    unread_count,
    upcoming_deadlines,
)
from notifications.models import Audience
from notifications.sources import NewsSource, get_feed_sources
from petitions.models import PetitionComment, PetitionStatusChange
from petitions.services import change_status
from petitions.tests.helpers import make_petition, make_type
from schedule.models import ChangeKind, LessonChange
from schedule.mutations import save_lesson_change
from schedule.tests.helpers import make_discipline, make_lesson, make_room, make_teacher

from .helpers import make_announcement, make_world, set_seen

NOW = "2026-11-11 12:00"
D = date(2026, 11, 11)


def _ctx(user, now=None):
    return student_context(user, now)


def _keys(user, now=None):
    return [i.key for i in build_feed(_ctx(user, now))]


class StudentScopeTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_university_item_visible_to_all_students(self):
        announcement = make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        key = f"news-{announcement.public_id}"
        for student in (self.w.ax, self.w.bx, self.w.cx, self.w.ay):
            self.assertIn(key, _keys(student))

    def test_faculty_item_only_for_that_faculty(self):
        announcement = make_announcement(self.w.sx, audience=Audience.FACULTY, faculty=self.w.fx)
        key = f"news-{announcement.public_id}"
        self.assertIn(key, _keys(self.w.ax))
        self.assertIn(key, _keys(self.w.cx))
        self.assertNotIn(key, _keys(self.w.ay))

    def test_group_item_only_for_that_group(self):
        announcement = make_announcement(self.w.sx, audience=Audience.GROUP, group=self.w.gx1)
        key = f"news-{announcement.public_id}"
        self.assertIn(key, _keys(self.w.ax))
        self.assertIn(key, _keys(self.w.bx))
        self.assertNotIn(key, _keys(self.w.cx))
        self.assertNotIn(key, _keys(self.w.ay))

    def test_unpublished_hidden_everywhere(self):
        announcement = make_announcement(
            self.w.sx,
            audience=Audience.UNIVERSITY,
            is_published=False,
            deadline=D + timedelta(days=1),
        )
        key = f"news-{announcement.public_id}"
        ctx = _ctx(self.w.ax)
        self.assertNotIn(key, _keys(self.w.ax))
        self.assertNotIn(key, [d.title for d in upcoming_deadlines(ctx, 10)])
        self.assertEqual(unread_count(ctx), 0)

    def test_other_students_personal_events_hidden(self):
        rtype = make_type("Справка")
        petition = make_petition(self.w.bx_profile, rtype)
        change_status(petition, self.w.sx, "submitted", "in_progress")
        PetitionComment.objects.create(
            petition=petition, author=self.w.sx, text="Комментарий", created_at=timezone.now()
        )
        term = make_term(code="t-2026-autumn")
        disc = make_discipline("Дисциплина-BX")
        item = make_item(self.w.gx1, disc, term)
        make_mark(self.w.bx_profile, item, 5, D, "Семинар")
        make_result(self.w.bx_profile, item, "5", date=D)

        keys = _keys(self.w.ax)
        self.assertNotIn(
            f"petition-status-{PetitionStatusChange.objects.filter(petition=petition).last().pk}",
            keys,
        )
        self.assertNotIn(f"petition-comment-{PetitionComment.objects.get().pk}", keys)
        self.assertNotIn(f"mark-{CurrentMark.objects.get().pk}", keys)
        self.assertNotIn(f"final-result-{FinalResult.objects.get().pk}", keys)

    def test_other_group_lesson_change_hidden(self):
        room = make_room("room-101")
        lesson = make_lesson([self.w.gx2], weekday=2, slot=1, room=room)
        change = save_lesson_change(
            LessonChange(
                weekly_lesson=lesson, original_date=D, kind=ChangeKind.CANCELLED, reason="Причина"
            )
        )
        self.assertNotIn(f"lesson-change-{change.pk}", _keys(self.w.ax))

    def test_shared_lesson_change_visible_to_both_groups(self):
        room = make_room("room-101")
        lesson = make_lesson([self.w.gx1, self.w.gx2], weekday=2, slot=1, room=room)
        change = save_lesson_change(
            LessonChange(
                weekly_lesson=lesson, original_date=D, kind=ChangeKind.CANCELLED, reason="Причина"
            )
        )
        key = f"lesson-change-{change.pk}"
        self.assertIn(key, _keys(self.w.ax))
        self.assertIn(key, _keys(self.w.cx))


class PetitionSourcesTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.rtype = make_type("Справка")

    def _petition(self):
        return make_petition(self.w.ax_profile, self.rtype)

    def test_staff_status_change_listed_with_link(self):
        petition = self._petition()
        change_status(petition, self.w.sx, "submitted", "in_progress")
        change_status(petition, self.w.sx, "in_progress", "ready")
        items = build_feed(_ctx(self.w.ax))
        status_items = [i for i in items if i.kind == "petition_status"]
        ready = next(i for i in status_items if "готова" in i.title)
        self.assertEqual(
            ready.url, reverse("petitions:detail", kwargs={"public_id": petition.public_id})
        )

    def test_rejection_comment_in_body(self):
        petition = self._petition()
        change_status(petition, self.w.sx, "submitted", "rejected", comment="Не хватает документов")
        items = build_feed(_ctx(self.w.ax))
        self.assertTrue(
            any("Не хватает документов" in i.body for i in items if i.kind == "petition_status")
        )

    def test_own_submission_not_listed(self):
        self._petition()
        keys = _keys(self.w.ax)
        self.assertFalse(any(k.startswith("petition-status-") for k in keys))

    def test_staff_comment_listed(self):
        petition = self._petition()
        comment = PetitionComment.objects.create(
            petition=petition,
            author=self.w.sx,
            text="Заберите документ в деканате",
            created_at=timezone.now(),
        )
        items = build_feed(_ctx(self.w.ax))
        comment = next(i for i in items if i.kind == "petition_comment")
        self.assertIn("Комментарий деканата", comment.title)
        self.assertEqual(comment.body, "Заберите документ в деканате")
        self.assertEqual(
            comment.url, reverse("petitions:detail", kwargs={"public_id": petition.public_id})
        )

    def test_status_change_via_service_listed(self):
        petition = self._petition()
        change_status(petition, self.w.sx, "submitted", "in_progress")
        keys = _keys(self.w.ax)
        self.assertTrue(any(k.startswith("petition-status-") for k in keys))


class LessonChangeSourceTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.room = make_room("room-101")
        cls.room2 = make_room("room-102")
        cls.teacher = make_teacher("Замена")

    def _lesson(self, weekday=2, groups=None):
        return make_lesson(groups or [self.w.gx1], weekday=weekday, slot=1, room=self.room)

    def test_cancelled_title_and_week_link(self):
        lesson = self._lesson()
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson, original_date=D, kind=ChangeKind.CANCELLED, reason="Причина"
            )
        )
        items = build_feed(_ctx(self.w.ax))
        item = next(i for i in items if i.kind == "lesson_change")
        self.assertIn("Отмена занятия", item.title)
        self.assertEqual(item.url, reverse("schedule:week_of", kwargs={"day": D}))

    def test_moved_title_mentions_new_date_and_room(self):
        lesson = self._lesson()
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=D,
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 12),
                new_slot=2,
                new_room=self.room2,
                reason="Причина",
            )
        )
        item = next(i for i in build_feed(_ctx(self.w.ax)) if i.kind == "lesson_change")
        self.assertIn("Перенос занятия", item.title)
        self.assertIn("12.11", item.title)
        self.assertIn("ауд. 102", item.title)

    def test_room_changed_title(self):
        lesson = self._lesson()
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=D,
                kind=ChangeKind.ROOM_CHANGED,
                new_room=self.room2,
                reason="Причина",
            )
        )
        item = next(i for i in build_feed(_ctx(self.w.ax)) if i.kind == "lesson_change")
        self.assertIn("Замена аудитории", item.title)

    def test_teacher_replaced_title(self):
        lesson = self._lesson()
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=D,
                kind=ChangeKind.TEACHER_REPLACED,
                new_teacher=self.teacher,
                reason="Причина",
            )
        )
        item = next(i for i in build_feed(_ctx(self.w.ax)) if i.kind == "lesson_change")
        self.assertIn("Замена преподавателя", item.title)

    def test_horizon_last_day_included(self):
        lesson = self._lesson()
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 25),
                kind=ChangeKind.CANCELLED,
                reason="Причина",
            )
        )
        self.assertTrue(any(k.startswith("lesson-change-") for k in _keys(self.w.ax)))

    def test_beyond_horizon_excluded(self):
        wed_lesson = self._lesson(weekday=2)
        save_lesson_change(
            LessonChange(
                weekly_lesson=wed_lesson,
                original_date=date(2026, 12, 2),
                kind=ChangeKind.CANCELLED,
                reason="Причина",
            )
        )
        thu_lesson = make_lesson([self.w.gx1], weekday=3, slot=1, room=self.room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=thu_lesson,
                original_date=date(2026, 11, 26),
                kind=ChangeKind.CANCELLED,
                reason="Причина",
            )
        )
        self.assertFalse(any(k.startswith("lesson-change-") for k in _keys(self.w.ax)))

    def test_past_original_with_future_new_date_included_links_new_week(self):
        lesson = self._lesson()
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 4),
                kind=ChangeKind.MOVED,
                new_date=date(2026, 11, 12),
                new_slot=2,
                reason="Причина",
            )
        )
        item = next(i for i in build_feed(_ctx(self.w.ax)) if i.kind == "lesson_change")
        self.assertEqual(item.url, reverse("schedule:week_of", kwargs={"day": date(2026, 11, 12)}))

    def test_past_change_excluded(self):
        lesson = self._lesson()
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 4),
                kind=ChangeKind.CANCELLED,
                reason="Причина",
            )
        )
        self.assertFalse(any(k.startswith("lesson-change-") for k in _keys(self.w.ax)))

    def test_edited_change_is_new_again(self):
        lesson = self._lesson()
        change = save_lesson_change(
            LessonChange(
                weekly_lesson=lesson, original_date=D, kind=ChangeKind.CANCELLED, reason="Причина"
            )
        )
        t = moscow(NOW)
        set_seen(self.w.ax, t)
        self.assertEqual(unread_count(_ctx(self.w.ax)), 0)
        with mock.patch("django.utils.timezone.now", return_value=t + timedelta(hours=1)):
            change.reason = "Новая причина"
            save_lesson_change(change)
        ctx = _ctx(self.w.ax, now=t + timedelta(hours=2))
        self.assertEqual(unread_count(ctx), 1)


class GradeSourcesTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.term = make_term(code="t-2026-autumn")
        cls.disc = make_discipline("Дисциплина")
        cls.item = make_item(cls.w.gx1, cls.disc, cls.term)

    def test_new_mark_listed_with_term_link(self):
        mark = make_mark(self.w.ax_profile, self.item, 5, D, "Семинар")
        items = build_feed(_ctx(self.w.ax))
        item = next(i for i in items if i.key == f"mark-{mark.pk}")
        self.assertEqual(
            item.url, reverse("academics:my_grades_term", kwargs={"term_code": self.term.code})
        )

    def test_new_final_result_listed(self):
        result = make_result(self.w.ax_profile, self.item, "5", date=D)
        self.assertIn(f"final-result-{result.pk}", _keys(self.w.ax))

    def test_retake_title_mentions_attempt(self):
        make_result(self.w.ax_profile, self.item, "2", attempt=1, date=date(2026, 10, 1))
        make_result(self.w.ax_profile, self.item, "3", attempt=2, date=date(2026, 10, 20))
        items = build_feed(_ctx(self.w.ax))
        self.assertTrue(any("попытка 2" in i.title for i in items if i.kind == "final_result"))

    def test_mark_created_via_save_validated_uses_frozen_clock(self):
        mark = make_mark(self.w.ax_profile, self.item, 4, D, "Семинар")
        self.assertEqual(mark.created_at, timezone.now())


class AdminEventsTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()
        cls.room = make_room("room-101")
        cls.term = make_term(code="t-2026-autumn")
        cls.disc = make_discipline("Дисциплина")
        cls.item = make_item(cls.w.gx1, cls.disc, cls.term)

    def setUp(self):
        self.client.force_login(self.w.root)

    def test_admin_lesson_change_appears(self):
        lesson = make_lesson([self.w.gx1], weekday=2, slot=1, room=self.room)
        response = self.client.post(
            reverse("admin:schedule_lessonchange_add"),
            {
                "weekly_lesson": lesson.pk,
                "original_date": "2026-11-11",
                "kind": "cancelled",
                "reason": "Отмена",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(any(k.startswith("lesson-change-") for k in _keys(self.w.ax)))

    def test_admin_mark_appears(self):
        response = self.client.post(
            reverse("admin:academics_currentmark_add"),
            {
                "student": self.w.ax_profile.pk,
                "curriculum_item": self.item.pk,
                "value": 5,
                "date": "2026-11-01",
                "kind": "Семинар",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(any(k.startswith("mark-") for k in _keys(self.w.ax)))


class FeedWindowTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_window_boundary(self):
        now = moscow(NOW)
        excluded = make_announcement(
            self.w.sx, audience=Audience.UNIVERSITY, published_at=now - timedelta(days=30)
        )
        included = make_announcement(
            self.w.sx,
            audience=Audience.UNIVERSITY,
            published_at=now - timedelta(days=30) + timedelta(minutes=1),
        )
        keys = _keys(self.w.ax)
        self.assertNotIn(f"news-{excluded.public_id}", keys)
        self.assertIn(f"news-{included.public_id}", keys)

    def test_future_item_excluded(self):
        future = make_announcement(
            self.w.sx, audience=Audience.UNIVERSITY, published_at=moscow(NOW) + timedelta(minutes=1)
        )
        self.assertNotIn(f"news-{future.public_id}", _keys(self.w.ax))

    def test_cap_50(self):
        for _ in range(55):
            make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        ctx = _ctx(self.w.ax)
        self.assertEqual(len(build_feed(ctx)), 50)
        self.assertEqual(badge_label(unread_count(ctx)), "50+")
        self.assertEqual(unread_count(ctx), 55)

    def test_newest_first_across_sources(self):
        now = moscow(NOW)
        term = make_term(code="t-2026-autumn")
        disc = make_discipline("Дисциплина")
        item = make_item(self.w.gx1, disc, term)
        rtype = make_type("Справка")
        petition = make_petition(self.w.ax_profile, rtype)

        news = make_announcement(
            self.w.sx, audience=Audience.UNIVERSITY, published_at=now - timedelta(hours=3)
        )
        mark = make_mark(self.w.ax_profile, item, 5, D, "Семинар")
        mark.created_at = now - timedelta(hours=2)
        mark.save(update_fields=["created_at"])
        comment = PetitionComment.objects.create(
            petition=petition,
            author=self.w.sx,
            text="Комментарий",
            created_at=now - timedelta(hours=1),
        )

        items = build_feed(_ctx(self.w.ax))
        self.assertEqual(
            [i.key for i in items],
            [f"petition-comment-{comment.pk}", f"mark-{mark.pk}", f"news-{news.public_id}"],
        )

    def test_empty_feed(self):
        self.assertEqual(build_feed(_ctx(self.w.ax)), [])


class DeadlinesTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_nearest_first_and_labels(self):
        make_announcement(
            self.w.sx, audience=Audience.UNIVERSITY, deadline=D + timedelta(days=5), title="A5"
        )
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY, deadline=D, title="A0")
        make_announcement(
            self.w.sx, audience=Audience.UNIVERSITY, deadline=D + timedelta(days=2), title="A2"
        )
        make_announcement(
            self.w.sx, audience=Audience.UNIVERSITY, deadline=D + timedelta(days=1), title="A1"
        )
        deadlines = upcoming_deadlines(_ctx(self.w.ax), 10)
        self.assertEqual([d.title for d in deadlines], ["A0", "A1", "A2", "A5"])
        self.assertEqual(
            [d.label for d in deadlines], ["сегодня", "завтра", "через 2 дня", "через 5 дней"]
        )

    def test_past_deadline_leaves_block_stays_in_feed(self):
        announcement = make_announcement(
            self.w.sx,
            audience=Audience.UNIVERSITY,
            deadline=D - timedelta(days=1),
            published_at=moscow(NOW) - timedelta(hours=5),
        )
        deadlines = upcoming_deadlines(_ctx(self.w.ax), 10)
        self.assertEqual(deadlines, [])
        items = build_feed(_ctx(self.w.ax))
        item = next(i for i in items if i.key == f"news-{announcement.public_id}")
        self.assertEqual(item.deadline_label, "срок прошёл")

    def test_old_announcement_with_future_deadline_in_block(self):
        announcement = make_announcement(
            self.w.sx,
            audience=Audience.UNIVERSITY,
            deadline=D + timedelta(days=3),
            published_at=moscow(NOW) - timedelta(days=40),
        )
        deadlines = upcoming_deadlines(_ctx(self.w.ax), 10)
        self.assertEqual([d.public_id for d in deadlines], [announcement.public_id])
        self.assertNotIn(f"news-{announcement.public_id}", _keys(self.w.ax))

    def test_limit(self):
        for i in range(12):
            make_announcement(
                self.w.sx, audience=Audience.UNIVERSITY, deadline=D + timedelta(days=i + 1)
            )
        self.assertEqual(len(upcoming_deadlines(_ctx(self.w.ax), 10)), 10)


class BeforeMidnightTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-09 23:59:59"

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_deadline_label(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY, deadline=date(2026, 11, 10))
        deadlines = upcoming_deadlines(_ctx(self.w.ax), 10)
        self.assertEqual(deadlines[0].label, "завтра")

    def test_deadline_today_leaves_block_after_midnight(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY, deadline=date(2026, 11, 9))
        self.assertEqual(len(upcoming_deadlines(_ctx(self.w.ax), 10)), 1)

    def test_lesson_today_leaves_horizon_after_midnight(self):
        room = make_room("room-101")
        lesson = make_lesson([self.w.gx1], weekday=0, slot=1, room=room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 9),
                kind=ChangeKind.CANCELLED,
                reason="Причина",
            )
        )
        self.assertTrue(any(k.startswith("lesson-change-") for k in _keys(self.w.ax)))


class AfterMidnightTests(FrozenClockMixin, TestCase):
    frozen_now = "2026-11-10 00:30:00"

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_deadline_label(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY, deadline=date(2026, 11, 10))
        deadlines = upcoming_deadlines(_ctx(self.w.ax), 10)
        self.assertEqual(deadlines[0].label, "сегодня")

    def test_deadline_today_leaves_block_after_midnight(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY, deadline=date(2026, 11, 9))
        self.assertEqual(len(upcoming_deadlines(_ctx(self.w.ax), 10)), 0)

    def test_lesson_today_leaves_horizon_after_midnight(self):
        room = make_room("room-101")
        lesson = make_lesson([self.w.gx1], weekday=0, slot=1, room=room)
        save_lesson_change(
            LessonChange(
                weekly_lesson=lesson,
                original_date=date(2026, 11, 9),
                kind=ChangeKind.CANCELLED,
                reason="Причина",
            )
        )
        self.assertFalse(any(k.startswith("lesson-change-") for k in _keys(self.w.ax)))


class UnreadTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_no_state_everything_new(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        ctx = _ctx(self.w.ax)
        self.assertEqual(unread_count(ctx), 2)
        self.assertTrue(all(i.is_new for i in build_feed(ctx)))

    def test_only_items_after_seen_are_new(self):
        now = moscow(NOW)
        make_announcement(
            self.w.sx, audience=Audience.UNIVERSITY, published_at=now - timedelta(hours=2)
        )
        make_announcement(
            self.w.sx, audience=Audience.UNIVERSITY, published_at=now - timedelta(minutes=30)
        )
        set_seen(self.w.ax, now - timedelta(hours=1))
        ctx = _ctx(self.w.ax)
        self.assertEqual(unread_count(ctx), 1)
        items = build_feed(ctx)
        self.assertEqual(sum(1 for i in items if i.is_new), 1)

    def test_unpublish_decrements_count(self):
        announcement = make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        self.assertEqual(unread_count(_ctx(self.w.ax)), 1)
        announcement.is_published = False
        announcement.save(update_fields=["is_published"])
        self.assertEqual(unread_count(_ctx(self.w.ax)), 0)

    def test_badge_label(self):
        self.assertEqual(badge_label(0), "")
        self.assertEqual(badge_label(7), "7")
        self.assertEqual(badge_label(50), "50")
        self.assertEqual(badge_label(51), "50+")

    def test_badge_for_staff_and_anonymous_is_empty(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        self.assertEqual(badge_for_user(self.w.sx), "")
        self.assertEqual(badge_for_user(self.w.root), "")


class SourceRegistryTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_default_registry_has_seven_sources(self):
        self.assertEqual(len(get_feed_sources()), 7)

    def test_feed_and_counter_use_registry(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY)
        rtype = make_type("Справка")
        petition = make_petition(self.w.ax_profile, rtype)
        change_status(petition, self.w.sx, "submitted", "in_progress")
        with mock.patch("notifications.feed.get_feed_sources", return_value=(NewsSource(),)):
            ctx = _ctx(self.w.ax)
            items = build_feed(ctx)
            self.assertTrue(items)
            self.assertTrue(all(i.kind == "news" for i in items))
            self.assertEqual(unread_count(ctx), len(items))


class HomeSummaryStudentTests(FrozenClockMixin, TestCase):
    frozen_now = NOW

    @classmethod
    def setUpTestData(cls):
        cls.w = make_world()

    def test_summary_has_student(self):
        summary = home_summary(self.w.ax)
        self.assertEqual(summary.student.pk, self.w.ax.student_profile.pk)
        with self.assertNumQueries(0):
            self.assertEqual(summary.student.group.name, "GX1")

    def test_summary_uses_given_now(self):
        make_announcement(self.w.sx, audience=Audience.UNIVERSITY, deadline=D, title="Сегодня")
        self.assertEqual(len(home_summary(self.w.ax).deadlines), 1)
        summary = home_summary(self.w.ax, moscow("2026-11-12 10:00"))
        self.assertEqual(summary.deadlines, [])
