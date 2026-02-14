from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_notifications),
    path("unread-count/", views.unread_count),
    path("<int:notif_id>/read/", views.mark_read),
    path("read-all/", views.mark_all_read),
]