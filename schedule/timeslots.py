"""Fixed bell schedule for the fictional university."""

from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class TimeSlot:
    number: int
    start: time
    end: time


TIME_SLOTS: tuple[TimeSlot, ...] = (
    TimeSlot(1, time(9, 0), time(10, 30)),
    TimeSlot(2, time(10, 40), time(12, 10)),
    TimeSlot(3, time(12, 55), time(14, 25)),
    TimeSlot(4, time(14, 35), time(16, 5)),
    TimeSlot(5, time(16, 15), time(17, 45)),
    TimeSlot(6, time(17, 55), time(19, 25)),
    TimeSlot(7, time(19, 35), time(21, 5)),
)

SLOT_CHOICES: list[tuple[int, str]] = [
    (s.number, f"{s.number} пара ({s.start:%H:%M}–{s.end:%H:%M})") for s in TIME_SLOTS
]

MAX_SLOT: int = len(TIME_SLOTS)


def get_slot(number: int) -> TimeSlot:
    for slot in TIME_SLOTS:
        if slot.number == number:
            return slot
    raise ValueError(f"Unknown slot {number}")
