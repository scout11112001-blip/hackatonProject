from django.urls import path

from . import views

app_name = "chat"
urlpatterns = [
    path("chat/", views.StudentChatView.as_view(), name="student"),
    path("chat/updates/", views.StudentChatUpdatesView.as_view(), name="student_updates"),
    path("staff/chats/", views.StaffChatListView.as_view(), name="staff_list"),
    path("staff/chats/<uuid:public_id>/", views.StaffDialogView.as_view(), name="staff_dialog"),
    path(
        "staff/chats/<uuid:public_id>/updates/",
        views.StaffDialogUpdatesView.as_view(),
        name="staff_updates",
    ),
]
