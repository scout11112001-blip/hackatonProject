from django.urls import path

from . import views

app_name = "academics"
urlpatterns = [
    path("grades/", views.StudentGradesView.as_view(), name="my_grades"),
    path("grades/<slug:term_code>/", views.StudentGradesView.as_view(), name="my_grades_term"),
    path(
        "staff/students/<int:pk>/grades/",
        views.StaffStudentGradesView.as_view(),
        name="staff_student_grades",
    ),
    path(
        "staff/students/<int:pk>/grades/<slug:term_code>/",
        views.StaffStudentGradesView.as_view(),
        name="staff_student_grades_term",
    ),
]
