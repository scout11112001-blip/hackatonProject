"""Mark the pre-existing demo schedule rows with their seed_key.

Strict matching (all fields + group names) is used so that admin-created rows
with a coincidentally equal old 4-field key are never overwritten.
"""

from django.db import migrations

LEGACY_LESSONS = [
    ("lesson-01", "Введение в цифровую дипломатию", "lecture", 0, 1, "Лебедев", "room-101", ("ЦД-101",)),
    ("lesson-02", "Английский язык", "seminar", 0, 2, "Назарова", "room-308", ("ЦД-101",)),
    ("lesson-03", "Микроэкономика", "lecture", 0, 2, "Воронцова", "room-114", ("ЭД-201",)),
    ("lesson-04", "Анализ данных на Python", "lab", 0, 3, "Глебов", "room-205", ("ЭД-201",)),
    ("lesson-05", "Английский язык", "seminar", 1, 1, "Назарова", "room-315", ("ЭД-201",)),
    ("lesson-06", "Теория международных отношений", "lecture", 1, 2, "Лебедев", "room-101", ("ЦД-101",)),
    ("lesson-07", "Микроэкономика", "seminar", 1, 2, "Воронцова", "room-402", ("ЭД-201",)),
    ("lesson-08", "Анализ данных на Python", "lab", 1, 3, "Глебов", "room-205", ("ЦД-101",)),
    ("lesson-09", "Философия", "lecture", 2, 1, "Фомин", "room-101", ("ЦД-101", "ЭД-201")),
    ("lesson-10", "Введение в цифровую дипломатию", "seminar", 2, 2, "Лебедев", "room-212", ("ЦД-101",)),
    ("lesson-11", "Микроэкономика", "seminar", 2, 3, "Воронцова", "room-402", ("ЭД-201",)),
    ("lesson-12", "Анализ данных на Python", "lab", 3, 2, "Глебов", "room-205", ("ЭД-201",)),
    ("lesson-13", "Английский язык", "seminar", 3, 3, "Назарова", "room-308", ("ЦД-101",)),
    ("lesson-14", "Теория международных отношений", "seminar", 3, 4, "Лебедев", "room-212", ("ЦД-101",)),
    ("lesson-15", "Английский язык", "seminar", 3, 4, "Назарова", "room-315", ("ЭД-201",)),
    ("lesson-16", "Микроэкономика", "lecture", 4, 1, "Воронцова", "room-114", ("ЭД-201",)),
    ("lesson-17", "Анализ данных на Python", "lab", 4, 2, "Глебов", "room-205", ("ЦД-101",)),
    ("lesson-18", "Философия", "seminar", 4, 3, "Фомин", "room-212", ("ЭД-201",)),
]

LEGACY_CHANGES = [
    ("change-1", "lesson-01", "cancelled", "Преподаватель на конференции"),
    ("change-2", "lesson-16", "cancelled", "Мероприятие факультета"),
    ("change-3", "lesson-08", "moved", "Перенос по просьбе преподавателя"),
    ("change-4", "lesson-18", "moved", "Перенос из-за олимпиады"),
    ("change-5", "lesson-13", "room_changed", "Ремонт в аудитории 308"),
    ("change-6", "lesson-07", "room_changed", "Аудитория занята мероприятием"),
    ("change-7", "lesson-10", "teacher_replaced", "Болезнь преподавателя"),
    ("change-8", "lesson-12", "teacher_replaced", "Командировка преподавателя"),
]


def mark_existing_demo_rows(apps, schema_editor) -> None:
    WeeklyLesson = apps.get_model("schedule", "WeeklyLesson")
    LessonChange = apps.get_model("schedule", "LessonChange")

    for key, discipline, lesson_type, weekday, slot, teacher, room, group_names in LEGACY_LESSONS:
        if WeeklyLesson.objects.filter(seed_key=key).exists():
            continue
        candidates = list(
            WeeklyLesson.objects.filter(
                seed_key="",
                discipline__name=discipline,
                lesson_type=lesson_type,
                weekday=weekday,
                slot=slot,
                teacher__last_name=teacher,
                room__code=room,
            )
        )
        candidates = [
            c
            for c in candidates
            if set(c.groups.values_list("name", flat=True)) == set(group_names)
        ]
        if len(candidates) == 1:
            candidate = candidates[0]
            candidate.seed_key = key
            candidate.save(update_fields=["seed_key"])

    for key, lesson_key, kind, reason in LEGACY_CHANGES:
        if LessonChange.objects.filter(seed_key=key).exists():
            continue
        candidates = list(
            LessonChange.objects.filter(
                seed_key="", weekly_lesson__seed_key=lesson_key, kind=kind, reason=reason
            )
        )
        if len(candidates) == 1:
            candidate = candidates[0]
            candidate.seed_key = key
            candidate.save(update_fields=["seed_key"])


class Migration(migrations.Migration):
    dependencies = [
        ("schedule", "0002_lessonchange_seed_key_weeklylesson_seed_key_and_more"),
        ("university", "0002_discipline_room_teacher"),
    ]

    operations = [migrations.RunPython(mark_existing_demo_rows, migrations.RunPython.noop)]
