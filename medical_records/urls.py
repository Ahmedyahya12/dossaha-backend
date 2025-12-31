from django.urls import path
from . import views

urlpatterns = [
     path("add/", views.create_record, name="create_record"),
     path("<str:pk>/update/", views.update_record, name="update_record"),
    path("<str:pk>/archive/", views.archive_record, name="arhive_record"),
    path("", views.list_recods, name="list_recods"),
    path("<str:pk>/", views.get_recod, name="get_recod"),
   
]
