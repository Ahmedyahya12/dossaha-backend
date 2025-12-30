from django.urls import path

from accounts.custom_token import CustomTokenObtainPairView
from . import views

urlpatterns = [
    path("register/medecin/", views.register_medecin, name="register"),
    path("activate/<str:token>/", views.activate_account, name="activate_account"),
 
    path("login", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
 
]
