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
                room = Room(code=bad, floor=1, number="199")
                with self.assertRaises(ValidationError):
                    room.full_clean()
        good = Room(code="room-1", floor=1, number="198")
        good.full_clean()

    def test_room_floor_out_of_range_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Room.objects.create(code="room-0", floor=0, number="000")

    def test_teacher_short_name(self):
        with_middle = Teacher(last_name="Лебедев", first_name="Аркадий", middle_name="Семёнович")
        self.assertEqual(with_middle.short_name, "Лебедев\u00a0А.\u00a0С.")
        without_middle = Teacher(last_name="Фомин", first_name="Павел")
        self.assertEqual(without_middle.short_name, "Фомин\u00a0П.")

    def test_duplicate_teacher_name_rejected(self):
        Teacher.objects.create(last_name="Иванов", first_name="Иван", middle_name="Иванович")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Teacher.objects.create(
                    last_name="Иванов", first_name="Иван", middle_name="Иванович"
                )


class RoomNumberTests(TestCase):
    def test_valid_numbers(self):
        for number, floor in (("101", 1), ("999", 9)):
            with self.subTest(number=number, floor=floor):
                room = Room(code=f"room-{number}", floor=floor, number=number)
                room.full_clean()

    def test_bad_number_is_field_error(self):
        for number in ("15", "1015", "a05", "012", "2a5", "20 5"):
            with self.subTest(number=number):
                room = Room(code=f"room-{number.replace(' ', '')}", floor=1, number=number)
                with self.assertRaises(ValidationError) as ctx:
                    room.full_clean()
                self.assertIn("number", ctx.exception.message_dict)
                self.assertNotIn(
                    "Этаж должен совпадать с первой цифрой номера аудитории.",
                    ctx.exception.message_dict.get("__all__", []),
                )

    def test_floor_out_of_range_is_field_error(self):
        for floor in (0, 10):
            with self.subTest(floor=floor):
                room = Room(code=f"room-f{floor}", floor=floor, number="101")
                with self.assertRaises(ValidationError) as ctx:
                    room.full_clean()
                self.assertIn("floor", ctx.exception.message_dict)

    def test_floor_must_match_first_digit(self):
        room = Room(code="room-205x", floor=3, number="205")
        with self.assertRaises(ValidationError) as ctx:
            room.full_clean()
        self.assertEqual(
            ctx.exception.message_dict["__all__"],
            ["Этаж должен совпадать с первой цифрой номера аудитории."],
        )

    def test_db_rejects_bad_number(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Room.objects.create(code="room-db1", floor=1, number="15")

    def test_db_rejects_mismatch(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Room.objects.create(code="room-db2", floor=3, number="205")

    def test_db_rejects_floor_10(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Room.objects.create(code="room-db3", floor=10, number="101")


class RoomMapCellTests(TestCase):
    def test_landmark_cell_rejected(self):
        for floor, cell, label in (
            (1, "S3", "Вход"),
            (2, "S1", "Деканат"),
            (3, "S5", "Библиотека"),
        ):
            with self.subTest(floor=floor, cell=cell):
                number = f"{floor}0{5 if cell != 'S1' else 1}"
                room = Room(code=f"room-{number}", floor=floor, number=number, map_cell=cell)
                with self.assertRaises(ValidationError) as ctx:
                    room.full_clean()
                self.assertIn(label, ctx.exception.messages[0])

    def test_same_landmark_cell_free_on_other_floor(self):
        room = Room(code="room-403", floor=4, number="403", map_cell="S3")
        room.full_clean()

    def test_same_cell_same_floor_rejected(self):
        Room.objects.create(code="room-102", floor=1, number="102", map_cell="N2")
        room = Room(code="room-103", floor=1, number="103", map_cell="N2")
        with self.assertRaises(ValidationError) as ctx:
            room.full_clean()
        self.assertIn("Это место на схеме этажа уже занято", ctx.exception.messages[0])
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Room.objects.create(code="room-104", floor=1, number="104", map_cell="N2")

    def test_same_cell_other_floor_ok(self):
        Room.objects.create(code="room-202", floor=2, number="202", map_cell="N2")
        Room.objects.create(code="room-302", floor=3, number="302", map_cell="N2")

    def test_many_rooms_without_cell_ok(self):
        for n in (1, 2, 3):
            Room.objects.create(code=f"room-10{n}", floor=1, number=f"10{n}")

    def test_db_rejects_unknown_cell(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Room.objects.create(code="room-105", floor=1, number="105", map_cell="N1")
