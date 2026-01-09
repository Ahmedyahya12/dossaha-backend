
import base64
import hashlib
from rest_framework.decorators import api_view
from rest_framework import serializers
from accounts.serializers import CurrentUserSerializer, SignUpSerializer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.serializers import ValidationError
from accounts.services.activation_serice import (
    activate_user_and_profile,
    validate_activation_token,
)
from rest_framework.permissions import IsAuthenticated
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
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes

from accounts.models import Role


def _fingerprint_from_public_pem(public_pem: str) -> str:
    """
    Fingerprint stable: SHA-256 du contenu DER/bytes du PEM (ici on prend le base64 PEM).
    """
    # Nettoyer PEM -> garder uniquement la partie base64
    lines = [
        l.strip() for l in public_pem.strip().splitlines() if l and "-----" not in l
    ]
    b64 = "".join(lines)

    try:
        key_bytes = base64.b64decode(b64)
    except Exception:
        # fallback: fingerprint sur le texte si le pem n'est pas bien formé
        key_bytes = public_pem.encode("utf-8")

    digest = hashlib.sha256(key_bytes).hexdigest()
    return f"sha256:{digest}"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_public_key(request):
    """
    POST /accounts/keys/public/
    Body: { "public_key_pem": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----" }

    - réservé aux médecins
    - exige status ACTIVE + email verified + profile is_verified
    - stocke public_key_pem + fingerprint + key_uploaded_at
    """
    user = request.user

    # 1) Check role
    if getattr(user, "role", None) != Role.MEDECIN:
        return Response(
            {"detail": "Endpoint réservé aux médecins."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # 2) Check account state
    if getattr(user, "status", None) != "ACTIVE":
        return Response(
            {"detail": "Compte non ACTIVE (PENDING/REJECTED)."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not getattr(user, "is_email_verified", False):
        return Response(
            {"detail": "Email non vérifié."}, status=status.HTTP_403_FORBIDDEN
        )

    if not hasattr(user, "profile") or not user.profile.is_verified:
        return Response(
            {"detail": "Profil non vérifié par admin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # 3) Validate input
    public_pem = request.data.get("public_key_pem")
    if not public_pem or not isinstance(public_pem, str):
        return Response(
            {"public_key_pem": "Ce champ est requis."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if "BEGIN PUBLIC KEY" not in public_pem or "END PUBLIC KEY" not in public_pem:
        return Response(
            {"public_key_pem": "Format PEM invalide (BEGIN/END PUBLIC KEY manquant)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 4) Save
    fp = _fingerprint_from_public_pem(public_pem)
    profile = user.profile

    # Option: empêcher l'écrasement si déjà présent (rotation plus tard)
    if profile.public_key_pem:
        return Response(
            {
                "detail": "Une clé publique existe déjà. Rotation à implémenter plus tard.",
                "fingerprint": profile.key_fingerprint,
            },
            status=status.HTTP_409_CONFLICT,
        )

    profile.public_key_pem = public_pem
    profile.key_fingerprint = fp.replace("sha256:", "")[:64]  # ton champ max_length=64
    profile.key_uploaded_at = timezone.now()
    profile.save(update_fields=["public_key_pem", "key_fingerprint", "key_uploaded_at"])

    return Response(
        {
            "detail": "Public key saved",
            "fingerprint": fp,
            "uploaded_at": profile.key_uploaded_at,
        },
        status=status.HTTP_201_CREATED,
    )


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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    serializer = CurrentUserSerializer(request.user)
    return Response(serializer.data)
