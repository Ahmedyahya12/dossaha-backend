from django.core.exceptions import ValidationError
from django.utils import timezone
from django.shortcuts import get_object_or_404
from accounts.models import MedecinProfile


def validate_activation_token(token):
    profile = get_object_or_404(MedecinProfile, activation_token=token)
    # print(profile.id, profile.activation_token_expire)

    if (
        profile.activation_token_expire is None
        or profile.activation_token_expire < timezone.now()
    ):
        print(f"Le token d'activation a expiré le {profile.activation_token_expire}")
        raise ValidationError(
            "Le token d'activation a expiré. Veuillez demander un nouveau lien."
        )

    return profile


def activate_user_and_profile(profile):
    user = profile.user
    user.is_email_verified = True  
    user.save(update_fields=["is_email_verified"])

    profile.activation_token_expire = None
    profile.activation_token = ""
    profile.save(update_fields=["activation_token_expire", "activation_token"])
    print(f"Le compte de {profile.user.email} a été activé avec succès.")
