"""Fictional chat demo data (create-only, never update)."""

from dataclasses import dataclass
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import StaffProfile, StudentProfile

from .models import AuthorRole, Dialog, Message


@dataclass(frozen=True)
class ChatSeedSummary:
    dialogs: int
    messages: int


@dataclass(frozen=True)
class ChatSeed:
    student: str
    key: str
    author: str
    hours_ago: int
    text: str


CHAT_SEEDS = [
    ChatSeed(
        "student1",
        "c-1-1",
        "student",
        30,
        "Здравствуйте! Когда можно забрать справку об обучении?",
    ),
    ChatSeed(
        "student1",
        "c-1-2",
        "staff1",
        28,
        "Добрый день! Справка будет готова в пятницу, кабинет деканата на 2 этаже.",
    ),
    ChatSeed(
        "student1", "c-1-3", "student", 27, "Спасибо! А можно получить её в электронном виде?"
    ),
    ChatSeed(
        "student1",
        "c-1-4",
        "staff1",
        3,
        "Да, можно. Подайте заявку «Справка об обучении» и укажите это в комментарии.",
    ),
    ChatSeed(
        "student3",
        "c-3-1",
        "student",
        6,
        "Добрый день! Подскажите, где посмотреть график пересдач?",
    ),
    ChatSeed(
        "student2",
        "c-2-1",
        "student",
        50,
        "Здравствуйте! Нужна ли справка для социальной стипендии?",
    ),
    ChatSeed(
        "student2",
        "c-2-2",
        "staff2",
        48,
        "Да, нужна справка о составе семьи. Принесите её в деканат.",
    ),
    ChatSeed("student2", "c-2-3", "student", 2, "Спасибо! Можно принести копию?"),
]

# Per-student read markers as (student_read_key, staff_read_key); None -> 0.
READ_MARKERS = {
    "student1": ("c-1-3", "c-1-3"),
    "student3": (None, None),
    "student2": ("c-2-2", "c-2-2"),
}


def seed_chat_demo(today: date) -> ChatSeedSummary:
    with transaction.atomic():
        students = {
            s.user.username: s
            for s in StudentProfile.objects.filter(
                user__username__in=("student1", "student2", "student3")
            )
        }
        staff = {
            s.user.username: s.user
            for s in StaffProfile.objects.filter(user__username__in=("staff1", "staff2"))
        }
        base = timezone.now()
        dialogs = 0
        messages = 0
        for student_username in ("student1", "student3", "student2"):
            seeds = [s for s in CHAT_SEEDS if s.student == student_username]
            first_key = seeds[0].key
            if Message.objects.filter(seed_key=first_key).exists():
                continue
            student = students[student_username]
            dialog, _ = Dialog.objects.get_or_create(student=student)
            ids = {}
            last_message = None
            for seed in seeds:
                author = student.user if seed.author == "student" else staff[seed.author]
                role = AuthorRole.STUDENT if seed.author == "student" else AuthorRole.STAFF
                created_at = base - timedelta(hours=seed.hours_ago)
                message = Message(
                    dialog=dialog,
                    author=author,
                    author_role=role,
                    text=seed.text,
                    created_at=created_at,
                    seed_key=seed.key,
                )
                message.full_clean()
                message.save()
                ids[seed.key] = message.pk
                last_message = message
                messages += 1
            student_marker, staff_marker = READ_MARKERS[student_username]
            Dialog.objects.filter(pk=dialog.pk).update(
                last_message_at=last_message.created_at,
                last_message_id=last_message.pk,
                student_read_id=ids[student_marker] if student_marker else 0,
                staff_read_id=ids[staff_marker] if staff_marker else 0,
            )
            dialogs += 1
    return ChatSeedSummary(dialogs=dialogs, messages=messages)
