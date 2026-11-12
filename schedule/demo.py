"""Fictional schedule demo data.

Re-running replaces the demo changes (of the 18 demo lessons) with fresh ones
for the current and next week relative to the run date.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from django.db import transaction

from schedule.models import LessonChange, WeeklyLesson
from schedule.mutations import save_lesson_change, save_weekly_lesson
from schedule.services import week_start
from university.models import Discipline, Room, StudyGroup, Teacher


@dataclass(frozen=True)
class ScheduleSeedSummary:
    rooms: int
    teachers: int
    disciplines: int
    weekly_lessons: int
    changes: int


@dataclass(frozen=True)
class RoomSeed:
    code: str
    floor: int
    number: str


@dataclass(frozen=True)
class TeacherSeed:
    last_name: str
    first_name: str
    middle_name: str
    title: str


@dataclass(frozen=True)
class DisciplineSeed:
    name: str
    short_name: str


@dataclass(frozen=True)
class LessonSeed:
    weekday: int
    slot: int
    discipline: str
    lesson_type: str
    teacher: str
    room: str
    groups: tuple[str, ...]


@dataclass(frozen=True)
class ChangeSeed:
    lesson_index: int
    week: int
    kind: str
    new_date_offset: int | None = None
    new_slot: int | None = None
    new_room: str | None = None
    new_teacher: str | None = None
    reason: str = ""


ROOM_SEEDS = [
    RoomSeed(code="room-101", floor=1, number="101"),
    RoomSeed(code="room-114", floor=1, number="114"),
    RoomSeed(code="room-205", floor=2, number="205"),
    RoomSeed(code="room-212", floor=2, number="212"),
    RoomSeed(code="room-308", floor=3, number="308"),
    RoomSeed(code="room-315", floor=3, number="315"),
    RoomSeed(code="room-402", floor=4, number="402"),
]

TEACHER_SEEDS = [
    TeacherSeed(
        last_name="Лебедев", first_name="Аркадий", middle_name="Семёнович", title="профессор"
    ),
    TeacherSeed(last_name="Воронцова", first_name="Ирина", middle_name="Олеговна", title="доцент"),
    TeacherSeed(
        last_name="Глебов",
        first_name="Тимур",
        middle_name="Русланович",
        title="старший преподаватель",
    ),
    TeacherSeed(last_name="Назарова", first_name="Вера", middle_name="Ильинична", title="доцент"),
    TeacherSeed(last_name="Фомин", first_name="Павел", middle_name="Андреевич", title=""),
    TeacherSeed(
        last_name="Шестакова", first_name="Лидия", middle_name="Петровна", title="ассистент"
    ),
]

DISCIPLINE_SEEDS = [
    DisciplineSeed(name="Введение в цифровую дипломатию", short_name="Цифр. дипломатия"),
    DisciplineSeed(name="Английский язык", short_name="Англ. яз."),
    DisciplineSeed(name="Теория международных отношений", short_name="ТМО"),
    DisciplineSeed(name="Анализ данных на Python", short_name="Анализ данных"),
    DisciplineSeed(name="Микроэкономика", short_name="Микроэк."),
    DisciplineSeed(name="Философия", short_name="Философия"),
]

LESSON_SEEDS = [
    LessonSeed(
        0, 1, "Введение в цифровую дипломатию", "lecture", "Лебедев", "room-101", ("ЦД-101",)
    ),
    LessonSeed(0, 2, "Английский язык", "seminar", "Назарова", "room-308", ("ЦД-101",)),
    LessonSeed(0, 2, "Микроэкономика", "lecture", "Воронцова", "room-114", ("ЭД-201",)),
    LessonSeed(0, 3, "Анализ данных на Python", "lab", "Глебов", "room-205", ("ЭД-201",)),
    LessonSeed(1, 1, "Английский язык", "seminar", "Назарова", "room-315", ("ЭД-201",)),
    LessonSeed(
        1, 2, "Теория международных отношений", "lecture", "Лебедев", "room-101", ("ЦД-101",)
    ),
    LessonSeed(1, 2, "Микроэкономика", "seminar", "Воронцова", "room-402", ("ЭД-201",)),
    LessonSeed(1, 3, "Анализ данных на Python", "lab", "Глебов", "room-205", ("ЦД-101",)),
    LessonSeed(2, 1, "Философия", "lecture", "Фомин", "room-101", ("ЦД-101", "ЭД-201")),
    LessonSeed(
        2, 2, "Введение в цифровую дипломатию", "seminar", "Лебедев", "room-212", ("ЦД-101",)
    ),
    LessonSeed(2, 3, "Микроэкономика", "seminar", "Воронцова", "room-402", ("ЭД-201",)),
    LessonSeed(3, 2, "Анализ данных на Python", "lab", "Глебов", "room-205", ("ЭД-201",)),
    LessonSeed(3, 3, "Английский язык", "seminar", "Назарова", "room-308", ("ЦД-101",)),
    LessonSeed(
        3, 4, "Теория международных отношений", "seminar", "Лебедев", "room-212", ("ЦД-101",)
    ),
    LessonSeed(3, 4, "Английский язык", "seminar", "Назарова", "room-315", ("ЭД-201",)),
    LessonSeed(4, 1, "Микроэкономика", "lecture", "Воронцова", "room-114", ("ЭД-201",)),
    LessonSeed(4, 2, "Анализ данных на Python", "lab", "Глебов", "room-205", ("ЦД-101",)),
    LessonSeed(4, 3, "Философия", "seminar", "Фомин", "room-212", ("ЭД-201",)),
]

CHANGE_SEEDS = [
    ChangeSeed(lesson_index=0, week=0, kind="cancelled", reason="Преподаватель на конференции"),
    ChangeSeed(lesson_index=15, week=1, kind="cancelled", reason="Мероприятие факультета"),
    ChangeSeed(
        lesson_index=7,
        week=0,
        kind="moved",
        new_date_offset=3,
        new_slot=5,
        reason="Перенос по просьбе преподавателя",
    ),
    ChangeSeed(
        lesson_index=17,
        week=0,
        kind="moved",
        new_date_offset=7,
        new_slot=4,
        reason="Перенос из-за олимпиады",
    ),
    ChangeSeed(
        lesson_index=12,
        week=0,
        kind="room_changed",
        new_room="room-402",
        reason="Ремонт в аудитории 308",
    ),
    ChangeSeed(
        lesson_index=6,
        week=1,
        kind="room_changed",
        new_room="room-114",
        reason="Аудитория занята мероприятием",
    ),
    ChangeSeed(
        lesson_index=9,
        week=0,
        kind="teacher_replaced",
        new_teacher="Шестакова",
        reason="Болезнь преподавателя",
    ),
    ChangeSeed(
        lesson_index=11,
        week=1,
        kind="teacher_replaced",
        new_teacher="Шестакова",
        reason="Командировка преподавателя",
    ),
]


def seed_schedule_demo(today: date) -> ScheduleSeedSummary:
    with transaction.atomic():
        rooms = {}
        for seed in ROOM_SEEDS:
            room, _ = Room.objects.update_or_create(
                code=seed.code, defaults={"floor": seed.floor, "number": seed.number}
            )
            rooms[seed.code] = room

        teachers = {}
        for seed in TEACHER_SEEDS:
            teacher, _ = Teacher.objects.update_or_create(
                last_name=seed.last_name,
                first_name=seed.first_name,
                middle_name=seed.middle_name,
                defaults={"title": seed.title},
            )
            teachers[seed.last_name] = teacher

        disciplines = {}
        for seed in DISCIPLINE_SEEDS:
            discipline, _ = Discipline.objects.update_or_create(
                name=seed.name, defaults={"short_name": seed.short_name}
            )
            disciplines[seed.name] = discipline

        groups = {name: StudyGroup.objects.get(name=name) for name in ("ЦД-101", "ЭД-201")}

        monday = week_start(today)
        valid_from = monday - timedelta(weeks=8)
        valid_until = monday + timedelta(weeks=12) - timedelta(days=1)

        lessons: list[WeeklyLesson] = []
        for seed in LESSON_SEEDS:
            discipline = disciplines[seed.discipline]
            lesson = WeeklyLesson.objects.filter(
                discipline=discipline,
                lesson_type=seed.lesson_type,
                weekday=seed.weekday,
                slot=seed.slot,
            ).first()
            if lesson is None:
                lesson = WeeklyLesson(
                    weekday=seed.weekday,
                    slot=seed.slot,
                    discipline=discipline,
                    lesson_type=seed.lesson_type,
                )
            lesson.teacher = teachers[seed.teacher]
            lesson.room = rooms[seed.room]
            lesson.valid_from = valid_from
            lesson.valid_until = valid_until
            lessons.append(lesson)

        # Refresh demo changes (spec 6.9 step 6) BEFORE saving lessons (step 7), so that
        # save_weekly_lesson -> validate_weekly_lesson(exclude_pk) does not see stale changes.
        existing_ids = [lesson.id for lesson in lessons if lesson.id is not None]
        LessonChange.objects.filter(weekly_lesson_id__in=existing_ids).delete()

        for seed, lesson in zip(LESSON_SEEDS, lessons, strict=True):
            save_weekly_lesson(lesson, [groups[name] for name in seed.groups])

        for seed in CHANGE_SEEDS:
            lesson = lessons[seed.lesson_index]
            original_date = monday + timedelta(days=7 * seed.week + lesson.weekday)
            kwargs = {
                "weekly_lesson": lesson,
                "original_date": original_date,
                "kind": seed.kind,
                "reason": seed.reason,
            }
            if seed.new_date_offset is not None:
                kwargs["new_date"] = monday + timedelta(days=seed.new_date_offset)
            if seed.new_slot is not None:
                kwargs["new_slot"] = seed.new_slot
            if seed.new_room is not None:
                kwargs["new_room"] = rooms[seed.new_room]
            if seed.new_teacher is not None:
                kwargs["new_teacher"] = teachers[seed.new_teacher]
            save_lesson_change(LessonChange(**kwargs))

    return ScheduleSeedSummary(
        rooms=len(ROOM_SEEDS),
        teachers=len(TEACHER_SEEDS),
        disciplines=len(DISCIPLINE_SEEDS),
        weekly_lessons=len(LESSON_SEEDS),
        changes=len(CHANGE_SEEDS),
    )
