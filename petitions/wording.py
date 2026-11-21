"""Russian wording that agrees with the kind of a document (TASK-017).

A certificate is "справка" (feminine), an application is "заявление" (neuter).
Where kinds are mixed the generic noun is "документ" (masculine): the plain
``PetitionStatus`` labels.
"""

from petitions.models import PetitionStatus, RequestKind

CERTIFICATE = RequestKind.CERTIFICATE.value
APPLICATION = RequestKind.APPLICATION.value

STATUS_LABELS = {
    CERTIFICATE: {
        "submitted": "Подана",
        "in_progress": "В работе",
        "ready": "Готова",
        "issued": "Выдана",
        "rejected": "Отклонена",
    },
    APPLICATION: {
        "submitted": "Подано",
        "in_progress": "В работе",
        "ready": "Готово",
        "issued": "Выдано",
        "rejected": "Отклонено",
    },
}

ACTION_LABELS = {
    CERTIFICATE: {
        "in_progress": "Взять в работу",
        "ready": "Отметить готовой",
        "issued": "Отметить выданной",
        "rejected": "Отклонить",
    },
    APPLICATION: {
        "in_progress": "Взять в работу",
        "ready": "Отметить готовым",
        "issued": "Отметить выданным",
        "rejected": "Отклонить",
    },
}

TEXTS = {
    CERTIFICATE: {
        "noun": "Справка",
        "submit": "Заказать справку",
        "submitted_title": "Справка заказана",
        "back_link": "К справке",
        "comment_required": "Для этой справки комментарий обязателен.",
        "subject_example": "Справка о периоде обучения",
    },
    APPLICATION: {
        "noun": "Заявление",
        "submit": "Подать заявление",
        "submitted_title": "Заявление подано",
        "back_link": "К заявлению",
        "comment_required": "Для этого заявления комментарий обязателен.",
        "subject_example": "Заявление на индивидуальный учебный план",
    },
}

NOTIFICATION_TITLES = {
    CERTIFICATE: {
        "in_progress": "«{name}» взята в работу",
        "ready": "«{name}» готова — заберите её в деканате",
        "issued": "«{name}» выдана",
        "rejected": "«{name}» отклонена",
    },
    APPLICATION: {
        "in_progress": "«{name}» взято в работу",
        "ready": "«{name}» готово — заберите его в деканате",
        "issued": "«{name}» выдано",
        "rejected": "«{name}» отклонено",
    },
}

DOCUMENT_FORMS = ("документ", "документа", "документов")


def _kind(kind: str) -> str:
    return kind if kind in TEXTS else CERTIFICATE


def status_label(status: str, kind: str) -> str:
    labels = STATUS_LABELS.get(kind)
    if labels is not None and status in labels:
        return labels[status]
    return dict(PetitionStatus.choices).get(status, status)


def action_label(status: str, kind: str) -> str:
    return ACTION_LABELS[_kind(kind)][status]


def text(kind: str, key: str) -> str:
    return TEXTS[_kind(kind)][key]


def notification_title(status: str, kind: str, name: str) -> str:
    template = NOTIFICATION_TITLES[_kind(kind)].get(status)
    if template is None:
        return f"«{name}»: статус «{status_label(status, kind)}»"
    return template.format(name=name)


def plural_ru(n: int, forms: tuple[str, str, str]) -> str:
    """Russian plural: (1 документ, 2 документа, 5 документов)."""
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]
