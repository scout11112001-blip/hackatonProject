from django.urls import path

from . import views

app_name = "campusmap"
urlpatterns = [
    path("map/", views.MapView.as_view(), name="map"),
    path("map/floor/<int:floor>/", views.MapView.as_view(), name="floor"),
    path("map/room/<slug:code>/", views.MapView.as_view(), name="room"),
]
