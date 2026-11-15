from datetime import date

from django.test import SimpleTestCase

from notifications.dates import relative_day_label, ru_plural


class RuPluralTests(SimpleTestCase):
    def test_forms(self):
        cases = {
            1: "день",
            2: "дня",
            4: "дня",
            5: "дней",
            11: "дней",
            12: "дней",
            14: "дней",
            21: "день",
            22: "дня",
            25: "дней",
            101: "день",
            111: "дней",
            112: "дней",
            0: "дней",
        }
        for n, expected in cases.items():
            with self.subTest(n=n):
                self.assertEqual(ru_plural(n, "день", "дня", "дней"), expected)


class RelativeDayLabelTests(SimpleTestCase):
    TODAY = date(2026, 11, 11)

    def test_past(self):
        self.assertEqual(relative_day_label(date(2026, 11, 10), self.TODAY), "срок прошёл")

    def test_today(self):
        self.assertEqual(relative_day_label(date(2026, 11, 11), self.TODAY), "сегодня")

    def test_tomorrow(self):
        self.assertEqual(relative_day_label(date(2026, 11, 12), self.TODAY), "завтра")

    def test_two_days(self):
        self.assertEqual(relative_day_label(date(2026, 11, 13), self.TODAY), "через 2 дня")

    def test_five_days(self):
        self.assertEqual(relative_day_label(date(2026, 11, 16), self.TODAY), "через 5 дней")

    def test_twenty_one_days(self):
        self.assertEqual(relative_day_label(date(2026, 12, 2), self.TODAY), "через 21 день")
