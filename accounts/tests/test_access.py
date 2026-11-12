from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from accounts.access import get_profile_for_role, role_required
from accounts.models import User
from accounts.selectors import groups_visible_to, students_visible_to

from .helpers import make_faculty, make_group, make_staff, make_student


class GetProfileForRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FX")
        cls.group = make_group(cls.faculty, "GX")
        cls.student = make_student("stu", cls.group, "REC-1")
        cls.staff = make_staff("stf", cls.faculty)

    def test_returns_own_student_profile(self):
        profile = get_profile_for_role(self.student, User.Role.STUDENT)
        self.assertEqual(profile, self.student.student_profile)

    def test_returns_own_staff_profile(self):
        profile = get_profile_for_role(self.staff, User.Role.STAFF)
        self.assertEqual(profile, self.staff.staff_profile)

    def test_student_asking_staff_denied(self):
        with self.assertRaises(PermissionDenied):
            get_profile_for_role(self.student, User.Role.STAFF)

    def test_staff_asking_student_denied(self):
        with self.assertRaises(PermissionDenied):
            get_profile_for_role(self.staff, User.Role.STUDENT)

    def test_superuser_denied_for_both(self):
        superuser = User.objects.create_superuser("root", password=None)
        with self.assertRaises(PermissionDenied):
            get_profile_for_role(superuser, User.Role.STUDENT)
        with self.assertRaises(PermissionDenied):
            get_profile_for_role(superuser, User.Role.STAFF)

    def test_role_without_profile_denied(self):
        user = User.objects.create_user(username="noprofile", role=User.Role.STUDENT)
        with self.assertRaises(PermissionDenied):
            get_profile_for_role(user, User.Role.STUDENT)

    def test_anonymous_denied(self):
        with self.assertRaises(PermissionDenied):
            get_profile_for_role(AnonymousUser(), User.Role.STUDENT)

    def test_inactive_user_denied(self):
        user = make_student("inactive-stu", self.group, "REC-INACTIVE")
        user.is_active = False
        user.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            get_profile_for_role(user, User.Role.STUDENT)

    def test_bad_role_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_profile_for_role(self.student, "admin")


class RoleRequiredDecoratorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty = make_faculty("FD")
        cls.group = make_group(cls.faculty, "GD")
        cls.staff = make_staff("stf-deco", cls.faculty)
        cls.student = make_student("stu-deco", cls.group, "REC-DECO")

    def test_staff_access(self):
        @role_required(User.Role.STAFF)
        def view(request):
            return HttpResponse("ok")

        request = RequestFactory().get("/")
        request.user = self.staff
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.profile, self.staff.staff_profile)

    def test_student_denied(self):
        @role_required(User.Role.STAFF)
        def view(request):
            return HttpResponse("ok")

        request = RequestFactory().get("/")
        request.user = self.student
        with self.assertRaises(PermissionDenied):
            view(request)


class StudentsVisibleToTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty_x = make_faculty("FX")
        cls.faculty_y = make_faculty("FY")
        cls.group_x = make_group(cls.faculty_x, "GX")
        cls.group_y = make_group(cls.faculty_y, "GY")
        cls.student_a = make_student("alpha", cls.group_x, "REC-A")
        cls.student_b = make_student("beta", cls.group_y, "REC-B")
        cls.student_c = make_student("gamma", cls.group_x, "REC-C")
        cls.staff_x = make_staff("sx", cls.faculty_x)
        cls.staff_y = make_staff("sy", cls.faculty_y)

    def test_staff_sees_own_faculty_students(self):
        qs = students_visible_to(self.staff_x)
        self.assertEqual(set(qs), {self.student_a.student_profile, self.student_c.student_profile})

    def test_staff_without_profile_sees_nothing(self):
        user = User.objects.create_user(username="noprofile-staff", role=User.Role.STAFF)
        self.assertFalse(students_visible_to(user).exists())

    def test_student_sees_only_self(self):
        qs = students_visible_to(self.student_a)
        self.assertEqual(list(qs), [self.student_a.student_profile])

    def test_superuser_sees_nothing(self):
        superuser = User.objects.create_superuser("root2", password=None)
        self.assertFalse(students_visible_to(superuser).exists())

    def test_anonymous_sees_nothing(self):
        self.assertFalse(students_visible_to(AnonymousUser()).exists())

    def test_inactive_student_hidden_from_staff(self):
        inactive = make_student("inactive-stu", self.group_x, "REC-INACTIVE")
        inactive.is_active = False
        inactive.save(update_fields=["is_active"])
        qs = students_visible_to(self.staff_x)
        self.assertNotIn(inactive.student_profile, list(qs))


class GroupsVisibleToTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.faculty_x = make_faculty("GX")
        cls.faculty_y = make_faculty("GY")
        cls.group_x1 = make_group(cls.faculty_x, "GX1")
        cls.group_x2 = make_group(cls.faculty_x, "GX2")
        cls.group_y = make_group(cls.faculty_y, "GY")
        cls.student = make_student("stu", cls.group_x1, "REC-1")
        cls.staff_x = make_staff("sx", cls.faculty_x)
        cls.staff_y = make_staff("sy", cls.faculty_y)

    def test_staff_sees_own_faculty_groups(self):
        qs = groups_visible_to(self.staff_x)
        self.assertEqual(set(qs), {self.group_x1, self.group_x2})

    def test_student_sees_only_own_group(self):
        qs = groups_visible_to(self.student)
        self.assertEqual(list(qs), [self.group_x1])

    def test_superuser_sees_nothing(self):
        superuser = User.objects.create_superuser("root-g", password=None)
        self.assertFalse(groups_visible_to(superuser).exists())

    def test_anonymous_sees_nothing(self):
        self.assertFalse(groups_visible_to(AnonymousUser()).exists())

    def test_staff_without_profile_sees_nothing(self):
        user = User.objects.create_user(username="noprofile-staff-g", role=User.Role.STAFF)
        self.assertFalse(groups_visible_to(user).exists())
