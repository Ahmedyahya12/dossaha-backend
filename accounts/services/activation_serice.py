from django.core.exceptions import ValidationError
from django.utils import timezone
from django.shortcuts import get_object_or_404
from accounts.models import MedecinProfile

def validate_activation_token(token):
    profile = get_object_or_404(MedecinProfile, activation_token=token)
    # print(profile.id, profile.activation_token_expire)

    if profile.activation_token_expire is None or profile.activation_token_expire < timezone.now():
        print(f"Le token d'activation a expiré le {profile.activation_token_expire}")
        raise ValidationError("Le token d'activation a expiré. Veuillez demander un nouveau lien.")

    return profile


def activate_user_and_profile(profile):
    profile.is_verified = True
    profile.activation_token_expire = None
    profile.activation_token = ""
    profile.user.is_active = True
    profile.user.save()
    profile.save()

    print(f"Le compte de {profile.user.email} a été activé avec succès.")
