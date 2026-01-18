# dashboard/urls.py
from django.urls import path
from .views import medical_dashboard_stats

urlpatterns = [
    path("dashboard/medical/", medical_dashboard_stats),
]
