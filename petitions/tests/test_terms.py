from django.test import SimpleTestCase

from petitions.terms import term_label


class TermLabelTests(SimpleTestCase):
    def test_singular_genitive(self):
        for days in (1, 21, 31, 51):
            with self.subTest(days=days):
                self.assertEqual(term_label(days), f"до {days} рабочего дня")

    def test_plural_genitive(self):
        for days in (2, 3, 4, 5, 10, 11, 12, 14, 15, 20, 22, 60):
            with self.subTest(days=days):
                self.assertEqual(term_label(days), f"до {days} рабочих дней")
