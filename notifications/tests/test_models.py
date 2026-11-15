from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.tests.helpers import make_faculty, make_group, make_staff
from core.testing import FrozenClockMixin
from notifications.constants import BODY_MAX_LENGTH, TITLE_MAX_LENGTH
from notifications.models import Announcement, Audience

from .helpers import make_announcement


class AnnouncementModelTests(FrozenClockMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX1")
        cls.author = make_staff("sx", cls.faculty)

    def _ann(self, **kwargs):
        return make_announcement(self.author, audience=Audience.UNIVERSITY, **kwargs)

    def test_valid_combinations(self):
        combos = [
            {"audience": Audience.UNIVERSITY},
            {"audience": Audience.FACULTY, "faculty": self.faculty},
            {"audience": Audience.GROUP, "group": self.group},
        ]
        for combo in combos:
            with self.subTest(combo=combo):
                announcement = make_announcement(self.author, **combo)
                announcement.full_clean()

    def test_invalid_combinations_full_clean(self):
        combos = [
            {"audience": Audience.UNIVERSITY, "faculty": self.faculty},
            {"audience": Audience.FACULTY},
            {"audience": Audience.FACULTY, "faculty": self.faculty, "group": self.group},
            {"audience": Audience.GROUP},
            {"audience": Audience.GROUP, "group": self.group, "faculty": self.faculty},
        ]
        for combo in combos:
            with self.subTest(combo=combo):
                announcement = Announcement(
                    author=self.author, title="Заголовок", body="Текст", **combo
                )
                with self.assertRaises(ValidationError) as ctx:
                    announcement.full_clean()
                self.assertIn(NON_FIELD_ERRORS, ctx.exception.error_dict)
                self.assertIn(
                    "Получатели не соответствуют аудитории",
                    ctx.exception.error_dict[NON_FIELD_ERRORS][0].messages[0],
                )

    def test_invalid_combination_db_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Announcement.objects.create(
                author=self.author,
                title="Заголовок",
                body="Текст",
                audience=Audience.FACULTY,
            )

    def test_lengths_are_constants(self):
        self.assertEqual(Announcement._meta.get_field("title").max_length, TITLE_MAX_LENGTH)
        self.assertEqual(Announcement._meta.get_field("body").max_length, BODY_MAX_LENGTH)

    def test_str_and_audience_label(self):
        university = self._ann(title="Новость университета")
        self.assertEqual(str(university), "Новость университета")
        self.assertEqual(university.audience_label, "Для всех студентов")

        faculty = make_announcement(
            self.author, audience=Audience.FACULTY, faculty=self.faculty, title="Новость факультета"
        )
        self.assertEqual(faculty.audience_label, "Факультет: Факультет FX")

        group = make_announcement(
            self.author, audience=Audience.GROUP, group=self.group, title="Новость группы"
        )
        self.assertEqual(group.audience_label, "Группа GX1")
