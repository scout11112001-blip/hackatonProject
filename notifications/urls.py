from django.urls import path

from . import views

app_name = "notifications"
urlpatterns = [
    path("notifications/", views.NotificationsView.as_view(), name="feed"),
    path(
        "staff/announcements/", views.StaffAnnouncementsView.as_view(), name="staff_announcements"
    ),
    path(
        "staff/announcements/<uuid:public_id>/unpublish/",
        views.StaffUnpublishView.as_view(),
        name="staff_unpublish",
    ),
]
