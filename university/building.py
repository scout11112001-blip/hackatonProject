"""The fictional building: a fixed grid of map cells and landmarks (one building)."""

from dataclasses import dataclass

from django.db import models

STAIRS_CELL = "N1"


class MapCell(models.TextChoices):
    N2 = "N2", "Верхний ряд, место 2"
    N3 = "N3", "Верхний ряд, место 3"
    N4 = "N4", "Верхний ряд, место 4"
    N5 = "N5", "Верхний ряд, место 5"
    S1 = "S1", "Нижний ряд, место 1"
    S2 = "S2", "Нижний ряд, место 2"
    S3 = "S3", "Нижний ряд, место 3"
    S4 = "S4", "Нижний ряд, место 4"
    S5 = "S5", "Нижний ряд, место 5"


@dataclass(frozen=True)
class Landmark:
    key: str
    label: str
    cells: tuple[str, ...]  # adjacent cells of one row
    floor: int | None  # None = every floor


LANDMARKS: tuple[Landmark, ...] = (
    Landmark("stairs", "Лестница", (STAIRS_CELL,), None),
    Landmark("entrance", "Вход", ("S3",), 1),
    Landmark("canteen", "Столовая", ("S4", "S5"), 1),
    Landmark("deanery", "Деканат", ("S1", "S2"), 2),
    Landmark("library", "Библиотека", ("S4", "S5"), 3),
)


def landmarks_on(floor: int) -> list[Landmark]:
    return [lm for lm in LANDMARKS if lm.floor is None or lm.floor == floor]


def blocked_cells(floor: int) -> dict[str, Landmark]:
    return {cell: lm for lm in landmarks_on(floor) for cell in lm.cells}
