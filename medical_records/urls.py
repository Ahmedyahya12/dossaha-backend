from django.urls import path
from . import views

urlpatterns = [
    # medicalrecord
    path("add/", views.create_record, name="create_record"),
    path("<str:pk>/update/", views.update_record, name="update_record"),
    path("<str:pk>/archive/", views.archive_record, name="arhive_record"),
    path("", views.list_recods, name="list_recods"),
    path("<str:pk>/", views.get_recod, name="get_recod"),
   
     # MedicalDocument endpoints (nested)
    path("<int:record_pk>/documents/", views.list_medical_documents, name="list_medical_documents"),
    path("<int:record_pk>/documents/<int:pk>/", views.get_medical_document, name="get_medical_document"),
    path("documents/create/", views.create_medical_document, name="create_medical_document"),
    
    path("<int:record_pk>/documents/<int:pk>/update/", views.update_medical_document, name="update_medical_document"),
    # path("<int:record_pk>/documents/<int:pk>/archive/", views.archive_medical_document, name="archive_medical_document"),
]
