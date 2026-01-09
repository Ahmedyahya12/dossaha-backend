from rest_framework.permissions import BasePermission
from accounts.models import Role


class IsActiveVerifiedMedecin(BasePermission):
    """
    - role=MEDECIN
    - status=ACTIVE
    - is_email_verified=True
    - profile.is_verified=True
    
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "role", None) != Role.MEDECIN:
            return False

        if getattr(user, "status", None) != "ACTIVE":
            return False

        if not getattr(user, "is_email_verified", False):
            return False

        if not hasattr(user, "profile") or not user.profile.is_verified:
            return False

        return True
