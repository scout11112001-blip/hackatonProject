from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from university.models import Faculty, Program, Room, StudyGroup, Teacher


class UniversityModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = Faculty.objects.create(code="FX", name="Факультет X")
        cls.program = Program.objects.create(faculty=cls.faculty, code="41.03.05", name="Программа")

    def test_course_out_of_range_rejected(self):
        for course in (0, 7):
            with self.subTest(course=course):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        StudyGroup.objects.create(
                            program=self.program, name=f"G{course}", course=course
                        )
        group = StudyGroup(program=self.program, name="GX", course=7)
        with self.assertRaises(ValidationError):
            group.full_clean()

    def test_program_unique_per_faculty(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Program.objects.create(faculty=self.faculty, code="41.03.05", name="Дубль")
        other = Faculty.objects.create(code="FY", name="Факультет Y")
        Program.objects.create(faculty=other, code="41.03.05", name="Тот же код")

    def test_group_faculty_property(self):
        group = StudyGroup.objects.create(program=self.program, name="ЦД-101", course=1)
        self.assertEqual(group.faculty, self.faculty)

    def test_room_code_validator(self):
        for bad in ("Room-1", "1room"):
            with self.subTest(code=bad):
                room = Room(code=bad, floor=1, number="999")
                with self.assertRaises(ValidationError):
                    room.full_clean()
        good = Room(code="room-1", floor=1, number="998")
        good.full_clean()

    def test_room_floor_out_of_range_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Room.objects.create(code="room-0", floor=0, number="000")

    def test_teacher_short_name(self):
        with_middle = Teacher(last_name="Лебедев", first_name="Аркадий", middle_name="Семёнович")
        self.assertEqual(with_middle.short_name, "Лебедев А. С.")
        without_middle = Teacher(last_name="Фомин", first_name="Павел")
        self.assertEqual(without_middle.short_name, "Фомин П.")

    def test_duplicate_teacher_name_rejected(self):
        Teacher.objects.create(last_name="Иванов", first_name="Иван", middle_name="Иванович")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Teacher.objects.create(
                    last_name="Иванов", first_name="Иван", middle_name="Иванович"
                )
