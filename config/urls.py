"""URL configuration for the deanery project."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("schedule.urls")),
    path("", include("academics.urls")),
    path("", include("petitions.urls")),
    path("", include("notifications.urls")),
    path("", include("campusmap.urls")),
    path("", include("core.urls")),
]
