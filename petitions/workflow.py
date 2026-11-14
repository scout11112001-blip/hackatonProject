"""Petition status workflow: a single explicit transition table."""

from petitions.models import PetitionStatus

SUBMITTED = PetitionStatus.SUBMITTED
IN_PROGRESS = PetitionStatus.IN_PROGRESS
READY = PetitionStatus.READY
ISSUED = PetitionStatus.ISSUED
REJECTED = PetitionStatus.REJECTED

TRANSITIONS: dict[str, tuple[str, ...]] = {
    SUBMITTED: (IN_PROGRESS, REJECTED),
    IN_PROGRESS: (READY, REJECTED),
    READY: (ISSUED,),
    ISSUED: (),
    REJECTED: (),
}

OPEN_STATUSES = frozenset({SUBMITTED, IN_PROGRESS})
COMMENT_REQUIRED_FOR = frozenset({REJECTED})
ACTION_LABELS = {
    IN_PROGRESS: "Взять в работу",
    READY: "Отметить готовой",
    ISSUED: "Отметить выданной",
    REJECTED: "Отклонить",
}


def allowed_transitions(status: str) -> tuple[str, ...]:
    return TRANSITIONS.get(status, ())


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in allowed_transitions(from_status)
