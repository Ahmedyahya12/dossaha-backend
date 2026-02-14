import base64
import hashlib

from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from accounts.models import CustomUser, Role
from accounts.serializers import CurrentUserSerializer, SignUpSerializer,PatientListSerializer
from accounts.services.activation_serice import activate_user_and_profile, validate_activation_token
from accounts.services.registration_service import (
    build_activation_link,
    create_medecin,
    create_profile,
    generate_and_save_activation_token,

    send_email_to_medecin,
    validate_registration_data,
)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import re


from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from medical_records.permissions import IsActiveVerifiedMedecin


import secrets
from django.db import transaction


from accounts.models import PatientProfile
from accounts.serializers import PatientListSerializer, PatientCreateSerializer

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsActiveVerifiedMedecin])
def my_patients(request):
    """
    GET /accounts/patients/
    retourne les patients créés par le médecin connecté
    """
    qs = CustomUser.objects.filter(
        role=Role.PATIENT,
        patient_profile__created_by=request.user
    ).order_by("-id")

    return Response(PatientListSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsActiveVerifiedMedecin])
def create_patient(request):
    """
    POST /accounts/patients/create/
    Body: { first_name, last_name, email }
    """
    ser = PatientCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    temp_password = secrets.token_urlsafe(10)  # mot de passe temporaire

    with transaction.atomic():
        patient = CustomUser.objects.create(
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            role=Role.PATIENT,
            status="ACTIVE",           # ou PENDING selon ta logique
            is_email_verified=False,   # tu peux gérer après
        )
        patient.set_password(temp_password)
        patient.save()

        PatientProfile.objects.create(
            user=patient,
            created_by=request.user
        )

    return Response(
        {
            "id": patient.id,
            "email": patient.email,
            "temp_password": temp_password,  # ✅ pour MVP (à retirer plus tard et envoyer par email)
        },
        status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_signing_key(request):
    """
    POST /accounts/keys/signing/
    Body: { "sig_public_key_pem": "-----BEGIN PUBLIC KEY-----...", "sig_key_fingerprint": "sha256:..." }
    """
    user = request.user
    profile = getattr(user, "profile", None)
    if not profile:
        return Response({"detail": "No profile"}, status=status.HTTP_400_BAD_REQUEST)

    sig_public = request.data.get("sig_public_key_pem")
    sig_fp = request.data.get("sig_key_fingerprint")

    if not sig_public or not sig_fp:
        return Response(
            {"detail": "sig_public_key_pem and sig_key_fingerprint are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile.sig_public_key_pem = sig_public
    profile.sig_key_fingerprint = sig_fp
    profile.sig_key_uploaded_at = timezone.now()
    profile.save(update_fields=["sig_public_key_pem", "sig_key_fingerprint", "sig_key_uploaded_at"])

    return Response({"ok": True, "sig_key_fingerprint": sig_fp}, status=status.HTTP_200_OK)



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def provision_keys(request):
    user = request.user
    deny = _require_medecin_active_verified(user)
    if deny:
        return deny

    profile = user.profile

    public_pem = request.data.get("public_key_pem")
    key_fp = request.data.get("key_fingerprint")
    sig_public = request.data.get("sig_public_key_pem")
    sig_fp = request.data.get("sig_key_fingerprint")
    wrapped_enc = request.data.get("wrapped_enc_private_key")
    wrapped_sig = request.data.get("wrapped_sig_private_key")
    force = bool(request.data.get("force", False))

    if not public_pem or not key_fp or not sig_public or not sig_fp:
        return Response({"detail": "Missing public/signing key fields"}, status=400)
    if not wrapped_enc or not wrapped_sig:
        return Response({"detail": "Missing wrapped private keys"}, status=400)

    # If already exists => prevent overwrite unless force
    if profile.public_key_pem and profile.key_fingerprint and not force:
        return Response({"detail": "KEYS_ALREADY_EXIST"}, status=status.HTTP_409_CONFLICT)

    # normalize fps (remove sha256:)
    if isinstance(key_fp, str) and key_fp.startswith("sha256:"):
        key_fp = key_fp.split("sha256:", 1)[1]
    if isinstance(sig_fp, str) and sig_fp.startswith("sha256:"):
        sig_fp = sig_fp.split("sha256:", 1)[1]

    profile.public_key_pem = public_pem
    profile.key_fingerprint = key_fp
    profile.key_uploaded_at = timezone.now()

    profile.sig_public_key_pem = sig_public
    profile.sig_key_fingerprint = sig_fp
    profile.sig_key_uploaded_at = timezone.now()

    profile.wrapped_enc_private_key = wrapped_enc
    profile.wrapped_sig_private_key = wrapped_sig

    profile.save(update_fields=[
        "public_key_pem","key_fingerprint","key_uploaded_at",
        "sig_public_key_pem","sig_key_fingerprint","sig_key_uploaded_at",
        "wrapped_enc_private_key","wrapped_sig_private_key",
    ])

    return Response({"ok": True}, status=200)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_wrapped_keys(request):
    user = request.user
    deny = _require_medecin_active_verified(user)
    if deny:
        return deny

    profile = user.profile
    if not profile.wrapped_enc_private_key or not profile.wrapped_sig_private_key:
        return Response({"detail": "NO_WRAPPED_KEYS"}, status=404)

    return Response({
        "key_fingerprint": f"sha256:{profile.key_fingerprint}" if profile.key_fingerprint else None,
        "sig_key_fingerprint": f"sha256:{profile.sig_key_fingerprint}" if profile.sig_key_fingerprint else None,
        "wrapped_enc_private_key": profile.wrapped_enc_private_key,
        "wrapped_sig_private_key": profile.wrapped_sig_private_key,
    }, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def rotate_keys(request):
    public_key_pem = request.data.get("public_key_pem")
    key_fingerprint = request.data.get("key_fingerprint")

    if not public_key_pem or not key_fingerprint:
        return Response({"detail": "Missing public_key_pem or key_fingerprint"}, status=400)

    # (اختياري) validation بسيط
    if "BEGIN PUBLIC KEY" not in public_key_pem:
        return Response({"detail": "Invalid public key format"}, status=400)

    if not re.match(r"^sha256:[A-Za-z0-9_-]{10,}$", key_fingerprint):
        return Response({"detail": "Invalid fingerprint format"}, status=400)

    profile = request.user.profile

    force = bool(request.data.get("force", False))

    if profile.public_key_pem and profile.key_fingerprint:
        if profile.key_fingerprint != key_fingerprint and not force:
            return Response(
                {"detail": "KEY_ROTATION_REQUIRED"},
                status=status.HTTP_409_CONFLICT
            )

    profile.public_key_pem = public_key_pem
    profile.key_fingerprint = key_fingerprint
    profile.save(update_fields=["public_key_pem", "key_fingerprint"])

    return Response({"detail": "KEYS_ROTATED"}, status=200)


def _extract_pem_b64(pem: str) -> str:
    """Extract base64 body from a PEM string."""
    lines = [line.strip() for line in pem.strip().splitlines()]
    body = [line for line in lines if line and not line.startswith("-----")]
    return "".join(body)


def fingerprint_from_public_pem(public_pem: str) -> str:
    """
    Return a stable fingerprint of a public key PEM: SHA-256 over decoded DER bytes.
    Output format: 'sha256:<hex>'.
    """
    b64 = _extract_pem_b64(public_pem)

    try:
        key_bytes = base64.b64decode(b64, validate=True)
    except Exception as exc:
        raise serializers.ValidationError(
            {"public_key_pem": "Invalid PEM content: base64 body is not valid."}
        ) from exc

    digest = hashlib.sha256(key_bytes).hexdigest()
    return f"sha256:{digest}"


def _require_medecin_active_verified(user) -> Response | None:
    """Return a DRF Response if user is not allowed, otherwise None."""
    if getattr(user, "role", None) != Role.MEDECIN:
        return Response(
            {"detail": "This endpoint is restricted to doctors."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if getattr(user, "status", None) != "ACTIVE":
        return Response(
            {"detail": "Account is not ACTIVE."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not getattr(user, "is_email_verified", False):
        return Response(
            {"detail": "Email is not verified."},
            status=status.HTTP_403_FORBIDDEN,
        )

    profile = getattr(user, "profile", None)
    if not profile or not getattr(profile, "is_verified", False):
        return Response(
            {"detail": "Profile is not verified by admin."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_public_key(request):
    """
    POST /accounts/keys/public/
    Body: { "public_key_pem": "-----BEGIN PUBLIC KEY-----\\n...\\n-----END PUBLIC KEY-----" }

    Stores: public_key_pem + key_fingerprint + key_uploaded_at
    """
    user = request.user

    deny = _require_medecin_active_verified(user)
    if deny:
        return deny

    public_pem = request.data.get("public_key_pem")
    if not public_pem or not isinstance(public_pem, str):
        return Response(
            {"public_key_pem": "This field is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if "BEGIN PUBLIC KEY" not in public_pem or "END PUBLIC KEY" not in public_pem:
        return Response(
            {"public_key_pem": "Invalid PEM format (missing BEGIN/END PUBLIC KEY)."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile = user.profile
    if getattr(profile, "public_key_pem", None):
        return Response(
            {
                "detail": "Public key already exists. Key rotation is not implemented yet.",
                "fingerprint": f"sha256:{profile.key_fingerprint}",
            },
            status=status.HTTP_409_CONFLICT,
        )

    fp = fingerprint_from_public_pem(public_pem)
    fp_hex = fp.split("sha256:", 1)[1]  # 64 hex chars

    profile.public_key_pem = public_pem
    profile.key_fingerprint = fp_hex
    profile.key_uploaded_at = timezone.now()
    profile.save(update_fields=["public_key_pem", "key_fingerprint", "key_uploaded_at"])

    return Response(
        {
            "detail": "Public key saved.",
            "fingerprint": fp,
            "uploaded_at": profile.key_uploaded_at,
        },
        status=status.HTTP_201_CREATED,
    )


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def register_medecin(request):
    """Create doctor account and send activation email."""
    serializer = SignUpSerializer(data=request.data)

    try:
        email = validate_registration_data(serializer)
        user = create_medecin(serializer)
        create_profile(user, request.data)

        token = generate_and_save_activation_token(user)
        activation_link = build_activation_link(token)
        send_email_to_medecin(user, activation_link)

    except serializers.ValidationError as exc:
        return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {"detail": "Account created. Please verify your email to activate it."},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def activate_account(request, token):
    """Activate account using token."""
    try:
        profile = validate_activation_token(token)
        activate_user_and_profile(profile)
        return Response({"detail": "Account activated successfully."})

    except ValidationError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response(
            {"detail": "Invalid activation token."},
            status=status.HTTP_404_NOT_FOUND,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Return current authenticated user."""
    return Response(CurrentUserSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_patients(request):
    """List up to 20 patients, optionally filtered by id (q)."""
    q = request.GET.get("q", "").strip()

    qs = CustomUser.objects.filter(role=Role.PATIENT)
    if q:
        qs = qs.filter(id__icontains=q)

    qs = qs.order_by("id")[:20]
    return Response(PatientListSerializer(qs, many=True).data)
