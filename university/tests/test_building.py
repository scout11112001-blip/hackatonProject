from django.test import SimpleTestCase

from university.building import (
    LANDMARKS,
    STAIRS_CELL,
    MapCell,
    blocked_cells,
    landmarks_on,
)


class BuildingTests(SimpleTestCase):
    def test_stairs_on_every_floor(self):
        for floor in range(1, 10):
            with self.subTest(floor=floor):
                labels = [lm.label for lm in landmarks_on(floor)]
                self.assertIn("Лестница", labels)
                self.assertIn(STAIRS_CELL, blocked_cells(floor))

    def test_floor_landmarks(self):
        self.assertEqual({lm.key for lm in landmarks_on(1)}, {"stairs", "entrance", "canteen"})
        self.assertEqual({lm.key for lm in landmarks_on(2)}, {"stairs", "deanery"})
        self.assertEqual({lm.key for lm in landmarks_on(3)}, {"stairs", "library"})
        self.assertEqual({lm.key for lm in landmarks_on(4)}, {"stairs"})

    def test_blocked_cells(self):
        self.assertEqual(set(blocked_cells(1)), {"N1", "S3", "S4", "S5"})

    def test_choices_exclude_stairs(self):
        self.assertNotIn(STAIRS_CELL, MapCell.values)

    def test_landmark_cells_adjacent_same_row(self):
        for lm in LANDMARKS:
            rows = {cell[0] for cell in lm.cells}
            self.assertEqual(len(rows), 1, f"{lm.key} spans more than one row")
            cols = sorted(int(cell[1:]) for cell in lm.cells)
            self.assertEqual(
                cols, list(range(cols[0], cols[0] + len(cols))), f"{lm.key} not adjacent"
            )
