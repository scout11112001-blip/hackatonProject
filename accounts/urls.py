from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"
urlpatterns = [
    path("login/", views.DeaneryLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("staff/students/", views.StaffStudentListView.as_view(), name="staff_student_list"),
    path(
        "staff/students/<int:pk>/",
        views.StaffStudentDetailView.as_view(),
        name="staff_student_detail",
    ),
]
