"""The only write path for schedule models in application code."""

from collections.abc import Sequence

from django.core.exceptions import ValidationError
from django.db import transaction

from university.models import StudyGroup

from .models import LessonChange, WeeklyLesson
from .validation import validate_weekly_lesson


def save_weekly_lesson(lesson: WeeklyLesson, groups: Sequence[StudyGroup]) -> WeeklyLesson:
    with transaction.atomic():
        lesson.full_clean()
        errors = validate_weekly_lesson(
            weekday=lesson.weekday,
            slot=lesson.slot,
            valid_from=lesson.valid_from,
            valid_until=lesson.valid_until,
            room_id=lesson.room_id,
            group_ids=[g.pk for g in groups],
            exclude_pk=lesson.pk,
        )
        if errors:
            raise ValidationError(errors)
        lesson.save()
        lesson.groups.set(groups)
        return lesson


def save_lesson_change(change: LessonChange) -> LessonChange:
    with transaction.atomic():
        change.full_clean()
        change.save()
        return change
