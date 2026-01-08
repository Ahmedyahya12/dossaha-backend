from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import AuthenticationFailed
from accounts.models import Role


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        # 0) 
        if user.role != Role.MEDECIN:
            raise AuthenticationFailed("Ce endpoint est réservé aux médecins.")

        # 1) 
        if not getattr(user, "is_email_verified", False):
            raise AuthenticationFailed("Veuillez activer votre email d'abord.")

        if user.status == "PENDING":
            raise AuthenticationFailed("Compte en attente d'approbation admin.")
        if user.status == "REJECTED":
            raise AuthenticationFailed("Compte rejeté par l'administration.")
        if user.status != "ACTIVE":
            raise AuthenticationFailed("Compte inactif.")

       
        if not hasattr(user, "profile"):
            raise AuthenticationFailed("Profil médecin introuvable. Contactez l'administration.")
        if not user.profile.is_verified:
            raise AuthenticationFailed("Compte médecin non vérifié par l'administration.")

        
        data["user"] = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "status": user.status,
            "is_email_verified": getattr(user, "is_email_verified", False),
            "is_verified": user.profile.is_verified,
            "specialite": user.profile.specialite,
        }

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
