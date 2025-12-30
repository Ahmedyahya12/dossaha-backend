from rest_framework.decorators import api_view
from rest_framework import serializers
from accounts.models import MedecinProfile
from accounts.serializers import SignUpSerializer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.serializers import ValidationError
from accounts.services.activation_serice import (
    activate_user_and_profile,
    validate_activation_token,
)
from accounts.services.registration_service import (
    build_activation_link,
    create_profile,
    create_medecin,
    generate_and_save_activation_token,
    send_email_to_medecin,
    validate_registration_data,
)
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def register_medecin(request):
    data = request.data
    serializer = SignUpSerializer(data=data)
    try:
        # Valider les données
        email = validate_registration_data(serializer)
        # Créer l'utilisateur
        user = create_medecin(serializer)
        # create  profile
        create_profile(user, data)
        # Générer le token
        token = generate_and_save_activation_token(user)
        # Construire le lien d'activation
        activation_link = build_activation_link(token)
        # Envoyer l'email
        send_email_to_medecin(user, activation_link)

    except serializers.ValidationError as e:
        return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            "detail": "Votre compte a été créé. Veuillez vérifier votre email pour l'activer."
        }
    )


@api_view(["GET"])
def activate_account(request, token):
    try:
        profile = validate_activation_token(token)
        activate_user_and_profile(profile)
        return Response({"detail": "Votre compte a été activé avec succès"})

    except ValidationError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    except Exception:

        return Response(
            {"error": "Jeton d’activation invalide."}, status=status.HTTP_404_NOT_FOUND
        )
