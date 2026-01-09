from django.urls import path

from accounts.custom_token import CustomTokenObtainPairView
from . import views

urlpatterns = [
        path("keys/public/", views.upload_public_key, name="upload_public_key"),

    path("register/medecin/", views.register_medecin, name="register"),
    path("activate/<str:token>/", views.activate_account, name="activate_account"),
    path("login", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("me/", views.get_current_user),
    # path("profile/", views.update_medecin_profile),
    # path("keys/public/", views.upload_public_key),
    # # admin
    # path("admin/medecins/pending/", views.list_pending_medecins),
    # path("admin/medecins/<int:user_id>/verify/", views.verify_medecin),
    # path("admin/medecins/<int:user_id>/reject/", views.reject_medecin),
]
