"""Feed sources registry.

Each ``FeedSource`` computes the personal feed items of one event kind from the
rows that already exist (no stored notification rows). To add a new kind (e.g.
chat in TASK-009), subclass ``FeedSource`` and append it to ``FEED_SOURCES``;
nothing else changes.
"""

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from typing import Any, ClassVar

from django.db.models import F, Q, QuerySet
from django.urls import reverse
from django.utils.text import Truncator

from academics.models import CurrentMark, FinalResult
from accounts.models import StudentProfile
from chat.constants import FEED_PREVIEW_CHARS
from chat.models import AuthorRole, Message
from petitions.models import PetitionComment, PetitionStatusChange
from schedule.models import LessonChange

from .constants import LESSON_CHANGE_HORIZON_DAYS
from .dates import relative_day_label
from .models import Announcement
from .selectors import announcements_for_student

STATUS_TITLES = {
    "in_progress": "Заявка «{name}» взята в работу",
    "ready": "Заявка «{name}» готова — заберите документ в деканате",
    "issued": "Заявка «{name}» выдана",
    "rejected": "Заявка «{name}» отклонена",
}


@dataclass(frozen=True)
class FeedContext:
    user_id: int
    student: StudentProfile
    group_id: int
    faculty_id: int
    now: datetime
    today: date
    window_start: datetime
    seen_until: datetime | None

    def is_new(self, ts: datetime) -> bool:
        return self.seen_until is None or ts > self.seen_until

    @property
    def horizon_end(self) -> date:
        return self.today + timedelta(days=LESSON_CHANGE_HORIZON_DAYS)


@dataclass(frozen=True)
class FeedItem:
    key: str
    kind: str
    tag: str
    timestamp: datetime
    title: str
    body: str = ""
    url: str = ""
    deadline: date | None = None
    deadline_label: str = ""
    audience_label: str = ""
    is_new: bool = False


class FeedSource:
    kind: ClassVar[str]
    tag: ClassVar[str]
    event_field: ClassVar[str]
    related: ClassVar[tuple[str, ...]] = ()

    def base_queryset(self, ctx: FeedContext) -> QuerySet:
        raise NotImplementedError

    def to_item(self, obj: Any, ctx: FeedContext) -> FeedItem:
        raise NotImplementedError

    def window_queryset(self, ctx: FeedContext) -> QuerySet:
        f = self.event_field
        return (
            self.base_queryset(ctx)
            .filter(**{f"{f}__gt": ctx.window_start, f"{f}__lte": ctx.now})
            .order_by()
        )

    def unread_values(self, ctx: FeedContext) -> QuerySet:
        qs = self.window_queryset(ctx)
        if ctx.seen_until is not None:
            qs = qs.filter(**{f"{self.event_field}__gt": ctx.seen_until})
        return qs.values_list(self.event_field)

    def latest(self, ctx: FeedContext, limit: int) -> list[FeedItem]:
        qs = (
            self.window_queryset(ctx)
            .select_related(*self.related)
            .order_by(f"-{self.event_field}", "-pk")[:limit]
        )
        return [
            replace(item, is_new=ctx.is_new(item.timestamp))
            for item in (self.to_item(o, ctx) for o in qs)
        ]


class NewsSource(FeedSource):
    kind = "news"
    tag = "Новость"
    event_field = "published_at"
    related = ("faculty", "group")

    def base_queryset(self, ctx: FeedContext) -> QuerySet:
        return announcements_for_student(ctx.student)

    def to_item(self, obj: Announcement, ctx: FeedContext) -> FeedItem:
        return FeedItem(
            key=f"news-{obj.public_id}",
            kind=self.kind,
            tag="Дедлайн" if obj.deadline else "Новость",
            timestamp=obj.published_at,
            title=obj.title,
            body=obj.body,
            deadline=obj.deadline,
            deadline_label=relative_day_label(obj.deadline, ctx.today) if obj.deadline else "",
            audience_label=obj.audience_label,
        )


class PetitionStatusSource(FeedSource):
    kind = "petition_status"
    tag = "Заявка"
    event_field = "created_at"
    related = ("petition__request_type",)

    def base_queryset(self, ctx: FeedContext) -> QuerySet:
        return PetitionStatusChange.objects.filter(petition__student_id=ctx.student.pk).exclude(
            actor_id=ctx.user_id
        )

    def to_item(self, obj: PetitionStatusChange, ctx: FeedContext) -> FeedItem:
        name = obj.petition.request_type.name
        title = STATUS_TITLES.get(obj.to_status, "").format(name=name)
        if not title:
            title = f"Заявка «{name}»: статус «{obj.get_to_status_display()}»"
        return FeedItem(
            key=f"petition-status-{obj.pk}",
            kind=self.kind,
            tag=self.tag,
            timestamp=obj.created_at,
            title=title,
            body=obj.comment,
            url=reverse("petitions:detail", kwargs={"public_id": obj.petition.public_id}),
        )


class PetitionCommentSource(FeedSource):
    kind = "petition_comment"
    tag = "Заявка"
    event_field = "created_at"
    related = ("petition__request_type",)

    def base_queryset(self, ctx: FeedContext) -> QuerySet:
        return PetitionComment.objects.filter(petition__student_id=ctx.student.pk).exclude(
            author_id=ctx.user_id
        )

    def to_item(self, obj: PetitionComment, ctx: FeedContext) -> FeedItem:
        name = obj.petition.request_type.name
        return FeedItem(
            key=f"petition-comment-{obj.pk}",
            kind=self.kind,
            tag=self.tag,
            timestamp=obj.created_at,
            title=f"Комментарий деканата к заявке «{name}»",
            body=obj.text,
            url=reverse("petitions:detail", kwargs={"public_id": obj.petition.public_id}),
        )


class LessonChangeSource(FeedSource):
    kind = "lesson_change"
    tag = "Расписание"
    event_field = "updated_at"
    related = ("weekly_lesson__discipline", "new_room", "new_teacher")

    def base_queryset(self, ctx: FeedContext) -> QuerySet:
        return LessonChange.objects.filter(weekly_lesson__groups=ctx.group_id).filter(
            Q(original_date__range=(ctx.today, ctx.horizon_end))
            | Q(new_date__range=(ctx.today, ctx.horizon_end))
        )

    def to_item(self, obj: LessonChange, ctx: FeedContext) -> FeedItem:
        lesson = obj.weekly_lesson
        when = f"{lesson.discipline.name}, {obj.original_date:%d.%m}, {lesson.slot} пара"
        if obj.kind == "cancelled":
            title = f"Отмена занятия: {when}"
        elif obj.kind == "moved":
            title = f"Перенос занятия: {when} → {obj.new_date:%d.%m}, {obj.new_slot} пара"
            if obj.new_room:
                title += f", {obj.new_room}"
        elif obj.kind == "room_changed":
            title = f"Замена аудитории: {when} → {obj.new_room}"
        else:
            title = f"Замена преподавателя: {when} → {obj.new_teacher.short_name}"
        if ctx.today <= obj.original_date <= ctx.horizon_end:
            affected_day = obj.original_date
        else:
            affected_day = obj.new_date
        return FeedItem(
            key=f"lesson-change-{obj.pk}",
            kind=self.kind,
            tag=self.tag,
            timestamp=obj.updated_at,
            title=title,
            body=obj.reason,
            url=reverse("schedule:week_of", kwargs={"day": affected_day}),
        )


class CurrentMarkSource(FeedSource):
    kind = "mark"
    tag = "Оценка"
    event_field = "created_at"
    related = ("curriculum_item__discipline", "curriculum_item__term")

    def base_queryset(self, ctx: FeedContext) -> QuerySet:
        return CurrentMark.objects.filter(student_id=ctx.student.pk)

    def to_item(self, obj: CurrentMark, ctx: FeedContext) -> FeedItem:
        discipline = obj.curriculum_item.discipline
        term = obj.curriculum_item.term
        return FeedItem(
            key=f"mark-{obj.pk}",
            kind=self.kind,
            tag=self.tag,
            timestamp=obj.created_at,
            title=f"Новая оценка {obj.value} — {discipline.name} ({obj.kind})",
            url=reverse("academics:my_grades_term", kwargs={"term_code": term.code}),
        )


class FinalResultSource(FeedSource):
    kind = "final_result"
    tag = "Оценка"
    event_field = "created_at"
    related = ("curriculum_item__discipline", "curriculum_item__term")

    def base_queryset(self, ctx: FeedContext) -> QuerySet:
        return FinalResult.objects.filter(student_id=ctx.student.pk)

    def to_item(self, obj: FinalResult, ctx: FeedContext) -> FeedItem:
        discipline = obj.curriculum_item.discipline
        term = obj.curriculum_item.term
        title = f"Итоговый результат — {discipline.name}: {obj.get_result_display()}"
        if obj.attempt > 1:
            title += f" (попытка {obj.attempt})"
        return FeedItem(
            key=f"final-result-{obj.pk}",
            kind=self.kind,
            tag=self.tag,
            timestamp=obj.created_at,
            title=title,
            url=reverse("academics:my_grades_term", kwargs={"term_code": term.code}),
        )


class ChatReplySource(FeedSource):
    kind = "chat_reply"
    tag = "Чат"
    event_field = "created_at"
    related = ()

    def base_queryset(self, ctx: FeedContext) -> QuerySet:
        return Message.objects.filter(
            dialog__student_id=ctx.student.pk,
            author_role=AuthorRole.STAFF,
            id__gt=F("dialog__student_read_id"),
        )

    def to_item(self, obj: Message, ctx: FeedContext) -> FeedItem:
        return FeedItem(
            key=f"chat-{obj.pk}",
            kind=self.kind,
            tag=self.tag,
            timestamp=obj.created_at,
            title="Новое сообщение от деканата",
            body=Truncator(obj.text).chars(FEED_PREVIEW_CHARS),
            url=reverse("chat:student"),
        )


FEED_SOURCES = (
    NewsSource(),
    PetitionStatusSource(),
    PetitionCommentSource(),
    LessonChangeSource(),
    CurrentMarkSource(),
    FinalResultSource(),
    ChatReplySource(),
)


def get_feed_sources() -> tuple[FeedSource, ...]:
    return FEED_SOURCES
