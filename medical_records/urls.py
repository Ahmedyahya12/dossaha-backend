from django.urls import path
from . import views

urlpatterns = [
    path("records/", views.list_records, name="list_records"),
    path("records/create/", views.create_record, name="create_record"),
    path("records/<int:record_id>/", views.get_record_detail, name="record_detail"),
    path(
        "records/<int:record_id>/documents/",
        views.create_document,
        name="create_document",
    ),
    path(
        "records/<int:record_id>/documents/<int:doc_id>/",
        views.get_document,
        name="get_document",
    ),
    path(
        "records/<int:record_id>/documents/<int:doc_id>/cipher/",
        views.get_document_cipher,
        name="document_cipher",
    ),
]
