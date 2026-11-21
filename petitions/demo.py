"""Fictional petitions demo data.

Request types are reference data (upsert by name). Demo petitions are created
only if their ``seed_key`` is absent — existing rows are never updated.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from accounts.models import StaffProfile, StudentProfile
from petitions.files import store_attachment
from petitions.models import Petition, PetitionComment, PetitionStatusChange, RequestType
from petitions.services import add_working_days

DEMO_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


@dataclass(frozen=True)
class PetitionsSeedSummary:
    types: int
    petitions: int
    attachments: int


REQUEST_TYPES = [
    (
        "Справка об обучении",
        "certificate",
        3,
        False,
        "Можно указать, куда нужна справка.",
        "Справка, подтверждающая факт обучения в университете.",
        False,
    ),
    (
        "Справка для стипендиального отдела",
        "certificate",
        3,
        True,
        "Обязательно укажите причину обращения.",
        "Справка для оформления стипендий и иных выплат.",
        False,
    ),
    (
        "Заявление на повторную промежуточную аттестацию",
        "application",
        10,
        True,
        "Обязательно укажите причину обращения.",
        "Заявление о повторной сдаче промежуточной аттестации.",
        False,
    ),
    (
        "Заявление на академический отпуск",
        "application",
        15,
        True,
        "Обязательно укажите причину обращения.",
        "Заявление о предоставлении академического отпуска.",
        False,
    ),
    (
        "Справка о поступлении",
        "certificate",
        3,
        False,
        "Можно указать, куда нужна справка.",
        "Подтверждает зачисление в университет.",
        False,
    ),
    (
        "Другая справка",
        "certificate",
        5,
        True,
        "Опишите, что нужно и для чего.",
        "Если нужной справки нет в списке.",
        True,
    ),
    (
        "Другое заявление",
        "application",
        5,
        True,
        "Опишите, что нужно и для чего.",
        "Если нужного заявления нет в списке.",
        True,
    ),
]

STUDENT_STAFF = {"student1": "staff1", "student2": "staff2", "student3": "staff1"}

PETITIONS = [
    {
        "seed_key": "p-1",
        "student": "student1",
        "type": "Справка об обучении",
        "age": 2,
        "path": ["submitted"],
        "comment": "Для предоставления по месту требования.",
        "files": ["spravka-zapros.pdf"],
    },
    {
        "seed_key": "p-2",
        "student": "student1",
        "type": "Справка для стипендиального отдела",
        "age": 4,
        "path": ["submitted", "in_progress"],
        "comment": "Для оформления повышенной стипендии.",
        "staff_comment": ("staff1", "Справка будет готова к пятнице."),
    },
    {
        "seed_key": "p-3",
        "student": "student3",
        "type": "Заявление на повторную промежуточную аттестацию",
        "age": 6,
        "path": ["submitted", "in_progress", "ready"],
        "comment": "Пропустила экзамен по болезни, справка прилагается.",
        "files": ["spravka-bolezn.pdf"],
    },
    {
        "seed_key": "p-4",
        "student": "student3",
        "type": "Заявление на академический отпуск",
        "age": 9,
        "path": ["submitted", "rejected"],
        "comment": "Прошу предоставить академический отпуск по семейным обстоятельствам.",
        "reject_comment": "Не приложены подтверждающие документы.",
    },
    {
        "seed_key": "p-5",
        "student": "student1",
        "type": "Справка об обучении",
        "age": 20,
        "path": ["submitted", "in_progress", "ready", "issued"],
        "comment": "Для военкомата.",
    },
    {
        "seed_key": "p-6",
        "student": "student2",
        "type": "Справка об обучении",
        "age": 1,
        "path": ["submitted"],
        "comment": "Для банка.",
        "files": ["zayavlenie.pdf"],
    },
    {
        "seed_key": "p-7",
        "student": "student2",
        "type": "Справка для стипендиального отдела",
        "age": 5,
        "path": ["submitted", "in_progress"],
        "comment": "Для назначения социальной стипендии.",
        "staff_comment": ("staff2", "Проверяем данные о стипендии."),
    },
    {
        "seed_key": "p-8",
        "student": "student1",
        "type": "Другая справка",
        "subject": "Справка о периоде обучения",
        "age": 3,
        "path": ["submitted", "in_progress"],
        "comment": "Нужна для оформления визы, с указанием дат начала и окончания обучения.",
    },
]


def seed_petitions_demo(today: date) -> PetitionsSeedSummary:
    with transaction.atomic():
        types = {}
        for name, kind, days, required, hint, description, subject_required in REQUEST_TYPES:
            types[name], _ = RequestType.objects.update_or_create(
                name=name,
                defaults={
                    "kind": kind,
                    "processing_days": days,
                    "comment_required": required,
                    "comment_hint": hint,
                    "description": description,
                    "subject_required": subject_required,
                    "is_active": True,
                },
            )

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
        created = 0
        attachments = 0
        for seed in PETITIONS:
            if Petition.objects.filter(seed_key=seed["seed_key"]).exists():
                continue
            student = students[seed["student"]]
            rtype = types[seed["type"]]
            created_at = base - timedelta(days=seed["age"])
            path = seed["path"]
            petition = Petition.objects.create(
                student=student,
                request_type=rtype,
                subject=seed.get("subject", ""),
                comment=seed["comment"],
                status=path[-1],
                created_at=created_at,
                status_changed_at=created_at,
                expected_ready_date=add_working_days(
                    timezone.localdate(created_at), rtype.processing_days
                ),
                seed_key=seed["seed_key"],
            )
            actor = staff[STUDENT_STAFF[seed["student"]]]
            steps = [("", "submitted", "", student.user)]
            for i in range(1, len(path)):
                comment = seed.get("reject_comment", "") if path[i] == "rejected" else ""
                steps.append((path[i - 1], path[i], comment, actor))
            for i, (from_s, to_s, comment, who) in enumerate(steps):
                PetitionStatusChange.objects.create(
                    petition=petition,
                    from_status=from_s,
                    to_status=to_s,
                    actor=who,
                    created_at=created_at + timedelta(hours=i * 20),
                    comment=comment,
                )
            if seed.get("staff_comment"):
                who, text = seed["staff_comment"]
                PetitionComment.objects.create(
                    petition=petition,
                    author=staff[who],
                    text=text,
                    created_at=created_at + timedelta(hours=20 * len(steps)),
                )
            for fname in seed.get("files", []):
                store_attachment(petition, ContentFile(DEMO_PDF), fname, len(DEMO_PDF))
                attachments += 1
            created += 1

    return PetitionsSeedSummary(
        types=len(REQUEST_TYPES), petitions=created, attachments=attachments
    )
