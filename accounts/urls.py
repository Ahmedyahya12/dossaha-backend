from django.urls import path

from accounts.custom_token import CustomTokenObtainPairView
from . import views

urlpatterns = [
    path("keys/public/", views.upload_public_key, name="upload_public_key"),
    path("register/medecin/", views.register_medecin, name="register"),
    path("activate/<str:token>/", views.activate_account, name="activate_account"),
    path("login", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("me/", views.get_current_user),
    path("patients/", views.list_patients),
    path("profile/keys/rotate/", views.rotate_keys, name="rotate-keys"),
    path("keys/signing/", views.upload_signing_key, name="keys-signing"),
    path("patients/", views.my_patients, name="my_patients"),
    path("patients/create/", views.create_patient, name="create_patient"),
    # path("profile/", views.update_medecin_profile),
    # path("keys/public/", views.upload_public_key),
    # # admin
    # path("admin/medecins/pending/", views.list_pending_medecins),
    # path("admin/medecins/<int:user_id>/verify/", views.verify_medecin),
    # path("admin/medecins/<int:user_id>/reject/", views.reject_medecin),
]
