from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.models import Role


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @staticmethod
    def auth_fail(code: str, message: str):
        raise AuthenticationFailed({"code": code, "detail": message})

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        if user.role != Role.MEDECIN:
            self.auth_fail("NOT_MEDECIN", "Ce endpoint est réservé aux médecins.")

        if not getattr(user, "is_email_verified", False):
            self.auth_fail(
                "EMAIL_NOT_VERIFIED", "Veuillez activer votre email d'abord."
            )

        if user.status == "PENDING":
            self.auth_fail(
                "PENDING_ADMIN_APPROVAL", "Compte en attente d'approbation admin."
            )
        if user.status == "REJECTED":
            self.auth_fail("REJECTED", "Compte rejeté par l'administration.")
        if user.status != "ACTIVE":
            self.auth_fail("INACTIVE", "Compte inactif.")

        if not hasattr(user, "profile"):
            self.auth_fail(
                "PROFILE_MISSING",
                "Profil médecin introuvable. Contactez l'administration.",
            )

        if not user.profile.is_verified:
            self.auth_fail(
                "MEDECIN_NOT_VERIFIED",
                "Compte médecin non vérifié par l'administration.",
            )

        data["user"] = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "status": user.status,
            "is_email_verified": getattr(user, "is_email_verified", False),
            "is_verified": user.profile.is_verified,
            "specialite": getattr(user.profile, "specialite", None),
        }

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
