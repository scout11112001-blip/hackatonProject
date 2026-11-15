"""Feed composition, unread counter and home summary."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.utils import timezone

from accounts.models import StudentProfile, User

from .constants import FEED_MAX_ITEMS, FEED_WINDOW_DAYS, HOME_ITEMS
from .dates import relative_day_label
from .models import NotificationState
from .selectors import announcements_for_student
from .sources import FeedContext, FeedItem, NewsSource, get_feed_sources


def student_context(
    user: AbstractBaseUser | AnonymousUser, now: datetime | None = None
) -> FeedContext | None:
    if not user.is_authenticated or not user.is_active or user.role != User.Role.STUDENT:
        return None
    student = (
        StudentProfile.objects.select_related("group__program").filter(user_id=user.pk).first()
    )
    if student is None:
        return None
    seen = (
        NotificationState.objects.filter(user_id=user.pk)
        .values_list("seen_until", flat=True)
        .first()
    )
    now = now or timezone.now()
    return FeedContext(
        user_id=user.pk,
        student=student,
        group_id=student.group_id,
        faculty_id=student.group.program.faculty_id,
        now=now,
        today=timezone.localdate(now),
        window_start=now - timedelta(days=FEED_WINDOW_DAYS),
        seen_until=seen,
    )


def build_feed(ctx: FeedContext) -> list[FeedItem]:
    items = [item for source in get_feed_sources() for item in source.latest(ctx, FEED_MAX_ITEMS)]
    items.sort(key=lambda i: (i.timestamp, i.key), reverse=True)
    return items[:FEED_MAX_ITEMS]


def unread_count(ctx: FeedContext) -> int:
    querysets = [s.unread_values(ctx) for s in get_feed_sources()]
    if not querysets:
        return 0
    return querysets[0].union(*querysets[1:], all=True).count()


def badge_label(count: int) -> str:
    if count == 0:
        return ""
    if count > FEED_MAX_ITEMS:
        return f"{FEED_MAX_ITEMS}+"
    return str(count)


def badge_for_user(user: AbstractBaseUser | AnonymousUser) -> str:
    ctx = student_context(user)
    if ctx is None:
        return ""
    return badge_label(unread_count(ctx))


@dataclass(frozen=True)
class DeadlineItem:
    public_id: UUID
    title: str
    deadline: date
    label: str
    audience_label: str


def upcoming_deadlines(ctx: FeedContext, limit: int) -> list[DeadlineItem]:
    announcements = (
        announcements_for_student(ctx.student)
        .filter(deadline__gte=ctx.today, published_at__lte=ctx.now)
        .select_related("faculty", "group")
        .order_by("deadline", "-published_at", "pk")[:limit]
    )
    return [
        DeadlineItem(
            public_id=a.public_id,
            title=a.title,
            deadline=a.deadline,
            label=relative_day_label(a.deadline, ctx.today),
            audience_label=a.audience_label,
        )
        for a in announcements
    ]


@dataclass(frozen=True)
class HomeSummary:
    deadlines: list[DeadlineItem]
    news: list[FeedItem]


def home_summary(user: AbstractBaseUser | AnonymousUser) -> HomeSummary | None:
    ctx = student_context(user)
    if ctx is None:
        return None
    deadlines = upcoming_deadlines(ctx, HOME_ITEMS)
    shown = {f"news-{d.public_id}" for d in deadlines}
    candidates = NewsSource().latest(ctx, HOME_ITEMS + len(shown))
    news = [item for item in candidates if item.key not in shown][:HOME_ITEMS]
    return HomeSummary(deadlines=deadlines, news=news)
