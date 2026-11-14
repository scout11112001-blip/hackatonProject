from django.urls import path

from . import views

app_name = "petitions"
urlpatterns = [
    path("requests/", views.MyPetitionsView.as_view(), name="my_list"),
    path("requests/new/", views.CatalogView.as_view(), name="catalog"),
    path("requests/new/<int:type_id>/", views.SubmitPetitionView.as_view(), name="submit"),
    path("requests/<uuid:public_id>/", views.StudentPetitionDetailView.as_view(), name="detail"),
    path("requests/<uuid:public_id>/submitted/", views.SubmittedView.as_view(), name="submitted"),
    path(
        "requests/<uuid:public_id>/files/<uuid:file_id>/",
        views.download_attachment,
        name="download",
    ),
    path("staff/requests/", views.StaffQueueView.as_view(), name="staff_queue"),
    path(
        "staff/requests/<uuid:public_id>/",
        views.StaffPetitionDetailView.as_view(),
        name="staff_detail",
    ),
    path(
        "staff/requests/<uuid:public_id>/status/",
        views.StaffTransitionView.as_view(),
        name="staff_transition",
    ),
    path(
        "staff/requests/<uuid:public_id>/comments/",
        views.StaffCommentView.as_view(),
        name="staff_comment",
    ),
]
