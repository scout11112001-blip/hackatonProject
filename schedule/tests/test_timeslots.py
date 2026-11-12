from datetime import time

from django.test import SimpleTestCase

from schedule.timeslots import MAX_SLOT, TIME_SLOTS, get_slot


class TimeSlotsTests(SimpleTestCase):
    def test_numbers_are_consecutive(self):
        self.assertEqual([s.number for s in TIME_SLOTS], list(range(1, MAX_SLOT + 1)))

    def test_each_start_before_end(self):
        for slot in TIME_SLOTS:
            self.assertLess(slot.start, slot.end)

    def test_slots_ordered_and_non_overlapping(self):
        for prev, curr in zip(TIME_SLOTS, TIME_SLOTS[1:], strict=False):
            self.assertLess(prev.end, curr.start)

    def test_get_slot(self):
        self.assertEqual(get_slot(2).start, time(10, 40))

    def test_get_slot_out_of_range_raises(self):
        for number in (0, 8):
            with self.subTest(number=number):
                with self.assertRaises(ValueError):
                    get_slot(number)
