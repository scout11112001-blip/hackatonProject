"""Fictional announcements demo data.

Announcements are created only if their ``seed_key`` is absent — existing rows
are never updated.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import StaffProfile
from notifications.models import Announcement, Audience
from university.models import Faculty, StudyGroup


@dataclass(frozen=True)
class AnnouncementSeed:
    key: str
    audience: str
    target: str | None  # faculty code, group name, or None for university
    author: str  # username
    title: str
    body: str
    age_hours: int  # published_at = now - age_hours
    deadline_offset: int | None
    published: bool = True


@dataclass(frozen=True)
class NotificationsSeedSummary:
    announcements: int  # created in this run


ANNOUNCEMENT_SEEDS = [
    AnnouncementSeed(
        "n-1",
        "university",
        None,
        "staff1",
        "Открыта запись в студенческие клубы",
        "Записаться можно в студенческом совете до конца месяца.\n"
        "Список клубов — на стенде у главного входа.",
        72,
        None,
    ),
    AnnouncementSeed(
        "n-2",
        "university",
        None,
        "staff1",
        "Анкета «Качество обучения»",
        "Пройдите анонимную анкету о качестве преподавания.\nСсылку пришлёт староста группы.",
        26,
        5,
    ),
    AnnouncementSeed(
        "n-3",
        "faculty",
        "FDD",
        "staff1",
        "Выбор темы курсовой работы",
        "Сообщите тему и научного руководителя в деканат.\nСписок тем — на кафедре.",
        50,
        1,
    ),
    AnnouncementSeed(
        "n-4",
        "group",
        "ЦД-101",
        "staff1",
        "Отчёт по учебной практике",
        "Сдайте отчёт старосте группы в бумажном виде.",
        5,
        3,
    ),
    AnnouncementSeed(
        "n-5",
        "faculty",
        "FAE",
        "staff2",
        "Эссе по микроэкономике",
        "Сдайте эссе на кафедру.\nОбъём — до 5 страниц.",
        30,
        2,
    ),
    AnnouncementSeed(
        "n-6",
        "group",
        "ЭД-201",
        "staff2",
        "Собрание группы ЭД-201",
        "В четверг после третьей пары, ауд. 114.",
        4,
        None,
    ),
    AnnouncementSeed(
        "n-7",
        "faculty",
        "FDD",
        "staff1",
        "Запись на факультативы",
        "Запись на факультативы весеннего семестра.",
        144,
        -2,
    ),
    AnnouncementSeed(
        "n-8",
        "faculty",
        "FDD",
        "staff1",
        "Изменение графика работы деканата",
        "График работы не изменился, объявление снято.",
        48,
        None,
        published=False,
    ),
    AnnouncementSeed(
        "n-9",
        "faculty",
        "FAE",
        "staff2",
        "Консультация по стипендиям",
        "Консультация перенесена, объявление снято.",
        20,
        None,
        published=False,
    ),
]


def seed_notifications_demo(today: date) -> NotificationsSeedSummary:
    with transaction.atomic():
        base = timezone.now()
        faculties = {f.code: f for f in Faculty.objects.filter(code__in=("FDD", "FAE"))}
        groups = {g.name: g for g in StudyGroup.objects.filter(name__in=("ЦД-101", "ЭД-201"))}
        authors = {
            s.user.username: s.user
            for s in StaffProfile.objects.filter(user__username__in=("staff1", "staff2"))
        }

        created = 0
        for seed in ANNOUNCEMENT_SEEDS:
            if Announcement.objects.filter(seed_key=seed.key).exists():
                continue
            published_at = base - timedelta(hours=seed.age_hours)
            if seed.audience == Audience.UNIVERSITY:
                faculty = None
                group = None
            elif seed.audience == Audience.FACULTY:
                faculty = faculties[seed.target]
                group = None
            else:
                faculty = None
                group = groups[seed.target]
            author = authors[seed.author]
            announcement = Announcement(
                title=seed.title,
                body=seed.body,
                audience=seed.audience,
                faculty=faculty,
                group=group,
                deadline=today + timedelta(days=seed.deadline_offset)
                if seed.deadline_offset is not None
                else None,
                author=author,
                published_at=published_at,
                is_published=seed.published,
                seed_key=seed.key,
            )
            if not seed.published:
                announcement.unpublished_at = published_at + timedelta(hours=1)
                announcement.unpublished_by = author
            announcement.full_clean()
            announcement.save()
            created += 1

    return NotificationsSeedSummary(announcements=created)
