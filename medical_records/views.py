from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from accounts.models import CustomUser, Role
from dossahabackend import settings
from medical_records.services.email_service import send_share_email

from .models import MedicalRecord, MedicalDocument, RecordKeyEnvelope
from .serializers import (
    DoctorLookupSerializer,
    MedicalRecordCreateSerializer,
    MedicalRecordListSerializer,
    MedicalRecordDetailSerializer,
    MedicalDocumentCreateSerializer,
    MedicalDocumentDetailSerializer,
    RevokeShareSerializer,
    ShareRecordSerializer,
)
from .permissions import IsActiveVerifiedMedecin
from django.core.mail import send_mail


def _can_access_record(user, record: MedicalRecord) -> bool:
    if record.created_by_id == user.id:
        return True
    return record.allowed_doctors.filter(id=user.id).exists()


@api_view(["POST"])
@permission_classes([IsActiveVerifiedMedecin])
def create_record(request):
    """
    POST /api/records/
    Body:
    {
      "patient_id": 12,
      "dek_envelope": {"encrypted_dek": "...", "key_fingerprint": "sha256:..."}
    }
    """
    ser = MedicalRecordCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    dek_env = ser.validated_data["dek_envelope"]
    encrypted_dek = dek_env["encrypted_dek"]
    key_fingerprint = dek_env.get("key_fingerprint")
    patient = ser.validated_data["patient"]
    # Optionnel: vérifier cohérence avec le profile de l'utilisateur
    profile_fp = getattr(
        getattr(request.user, "profile", None), "key_fingerprint", None
    )
    # if profile_fp and key_fingerprint and profile_fp != key_fingerprint:
    #   return Response({"detail": "Fingerprint mismatch"}, status=status.HTTP_400_BAD_REQUEST)

    record = MedicalRecord.objects.create(
        patient=patient,
        created_by=request.user,
    )

    RecordKeyEnvelope.objects.create(
        record=record,
        doctor=request.user,
        encrypted_dek=encrypted_dek,
        key_fingerprint=key_fingerprint,
    )

    return Response(
        {"id": record.id, "patient_id": record.patient_id, "status": record.status},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsActiveVerifiedMedecin])
def list_records(request):
    """
    GET /api/records/
     records (owner أو allowed)
    + my_dek_envelope
    """
    qs = (
        MedicalRecord.objects.filter(
            Q(created_by=request.user) | Q(allowed_doctors=request.user)
        )
        .distinct()
        .order_by("-created_at")
    )

    ser = MedicalRecordListSerializer(qs, many=True, context={"request": request})
    return Response(ser.data)


@api_view(["GET"])
@permission_classes([IsActiveVerifiedMedecin])
def get_record_detail(request, record_id: int):
    """
    GET /api/records/<id>/
     record + documents + my_dek_envelope
    """
    record = MedicalRecord.objects.prefetch_related("documents", "key_envelopes").get(
        id=record_id
    )

    if not _can_access_record(request.user, record):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    record.touch_access()

    ser = MedicalRecordDetailSerializer(record, context={"request": request})
    return Response(ser.data)


@api_view(["POST"])
@permission_classes([IsActiveVerifiedMedecin])
def create_document(request, record_id: int):
    """
    POST /api/records/<record_id>/documents/
    Body: encrypted payload + signature metadata
    """
    record = MedicalRecord.objects.get(id=record_id)

    if not _can_access_record(request.user, record):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    has_env = record.key_envelopes.filter(doctor=request.user, is_active=True).exists()
    if not has_env:
        return Response(
            {"detail": "No active DEK envelope for this user"},
            status=status.HTTP_403_FORBIDDEN,
        )

    ser = MedicalDocumentCreateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data

    doc = MedicalDocument.objects.create(
        record=record,
        document_type=data["document_type"],
        title=data["title"],
        created_by=request.user,
        encrypted_payload=data["encrypted_payload"],
        payload_iv=data["payload_iv"],
        payload_tag=data["payload_tag"],
        payload_hash=data["payload_hash"],
        signature=data["signature"],
        signed_by=request.user,
        signed_at=timezone.now(),
        signing_key_fingerprint=data.get("signing_key_fingerprint"),
    )

    return Response(
        {"id": doc.id, "record_id": record.id, "title": doc.title},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsActiveVerifiedMedecin])
def get_document(request, record_id: int, doc_id: int):
    """
    GET /api/records/<record_id>/documents/<doc_id>/
     ciphertext + signature metadata
    """
    record = MedicalRecord.objects.get(id=record_id)
    if not _can_access_record(request.user, record):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    has_env = record.key_envelopes.filter(doctor=request.user, is_active=True).exists()
    if not has_env:
        return Response(
            {"detail": "No active DEK envelope for this user"},
            status=status.HTTP_403_FORBIDDEN,
        )

    doc = MedicalDocument.objects.get(id=doc_id, record=record)

    ser = MedicalDocumentDetailSerializer(doc)
    return Response(ser.data)


@api_view(["GET"])
@permission_classes([IsActiveVerifiedMedecin])
def get_document_cipher(request, record_id: int, doc_id: int):
    record = get_object_or_404(MedicalRecord, id=record_id)

    # صلاحيات الوصول
    if not _can_access_record(request.user, record):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    # لازم يكون عنده envelope فعال
    has_env = record.key_envelopes.filter(doctor=request.user, is_active=True).exists()
    if not has_env:
        return Response({"detail": "No active DEK envelope"}, status=status.HTTP_403_FORBIDDEN)

    # doc + signer profile (لتفادي queries)
    doc = get_object_or_404(
        MedicalDocument.objects.select_related("signed_by", "signed_by__profile"),
        id=doc_id,
        record=record,
    )

    # signer info
    signed_by_data = None
    signer_profile = None

    if doc.signed_by:
        signer_profile = getattr(doc.signed_by, "profile", None)

        signed_by_data = {
            "id": doc.signed_by.id,
            "name": doc.signed_by.get_full_name() or doc.signed_by.email,

            # ✅ مفاتيح التوقيع (RSA-PSS) للتحقق
            "sig_public_key_pem": getattr(signer_profile, "sig_public_key_pem", None),
            "sig_key_fingerprint": getattr(signer_profile, "sig_key_fingerprint", None),

            # ✅ (اختياري) نحتفظ بالمفاتيح القديمة OAEP (ما يكسر القديم)
            "public_key_pem": getattr(signer_profile, "public_key_pem", None),
            "key_fingerprint": getattr(signer_profile, "key_fingerprint", None),
        }

    return Response(
        {
            "id": doc.id,
            "record_id": record.id,
            "title": doc.title,
            "document_type": doc.document_type,

            # ciphertext (AES-GCM)
            "encrypted_payload": doc.encrypted_payload,
            "payload_iv": doc.payload_iv,
            "payload_tag": doc.payload_tag,

            # integrity + signature
            "payload_hash": doc.payload_hash,             # موجود سابقًا
            "signature": doc.signature,                   # موجود سابقًا
            "signed_by": signed_by_data,                  # كان موجود عندك (مع إضافة sig fields)
            "signed_at": doc.signed_at,

            # ✅ fingerprint المفتاح الذي استُخدم وقت التوقيع (للتحقق من rotation)
            "signing_key_fingerprint": doc.signing_key_fingerprint,
        },
        status=status.HTTP_200_OK,
    )

# sprint 3 started here


@api_view(["GET"])
@permission_classes([IsActiveVerifiedMedecin])
def doctor_lookup(request):
    email = request.GET.get("email", "").strip().lower()
    if not email:
        return Response(
            {"detail": "email is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    doctor = get_object_or_404(
        CustomUser.objects.select_related("profile"),
        email=email,
        role=Role.MEDECIN,
        status="ACTIVE",
        is_email_verified=True,
        profile__is_verified=True,
    )

    if not doctor.profile.public_key_pem:
        return Response(
            {"detail": "Doctor has no public key uploaded"},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(DoctorLookupSerializer(doctor).data)


@api_view(["POST"])
@permission_classes([IsActiveVerifiedMedecin])
def share_record(request, record_id: int):
    record = get_object_or_404(MedicalRecord, id=record_id)

    # only owner can share (recommandé)
    if record.created_by_id != request.user.id:
        return Response(
            {"detail": "Only owner can share this record"},
            status=status.HTTP_403_FORBIDDEN,
        )

    ser = ShareRecordSerializer(data=request.data)
    ser.is_valid(raise_exception=True)

    doctor_email = ser.validated_data["doctor_email"].lower()
    dek_env = ser.validated_data["dek_envelope"]

    target = get_object_or_404(
        CustomUser.objects.select_related("profile"),
        email=doctor_email,
        role=Role.MEDECIN,
        status="ACTIVE",
        is_email_verified=True,
        profile__is_verified=True,
    )

    if not target.profile.public_key_pem:
        return Response(
            {"detail": "Target doctor has no public key"},
            status=status.HTTP_409_CONFLICT,
        )

    # create/update access list
    record.allowed_doctors.add(target)

    # create envelope
    env, created = RecordKeyEnvelope.objects.get_or_create(
        record=record,
        doctor=target,
        defaults={
            "encrypted_dek": dek_env["encrypted_dek"],
            "key_fingerprint": dek_env.get("key_fingerprint"),
            "is_active": True,
            "shared_by": request.user,  # 👈 مهم
        },
    )

    if not created:
        # ✅ update envelope (rotation / re-share)
        env.encrypted_dek = dek_env["encrypted_dek"]
        env.key_fingerprint = dek_env.get("key_fingerprint")
        env.is_active = True
        env.shared_by = request.user
        env.save(
            update_fields=["encrypted_dek", "key_fingerprint", "is_active", "shared_by"]
        )

    return Response(
        {"detail": "Record shared/updated successfully", "record_id": record.id},
        status=status.HTTP_201_CREATED,
    )

    # notify by email
    from_name = request.user.get_full_name() or request.user.email
    to_name = target.get_full_name() or target.email

    send_share_email(
        to_email=target.email,
        to_name=to_name,
        from_name=from_name,
        record_id=record.id,
    )

    return Response(
        {
            "detail": "Record shared successfully",
            "record_id": record.id,
            "shared_with": {
                "id": target.id,
                "email": target.email,
                "name": target.get_full_name() or target.email,
            },
            "envelope_id": env.id,
            "created_at": env.created_at,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsActiveVerifiedMedecin])
def list_shared_with_me(request):
    qs = MedicalRecord.objects.filter(allowed_doctors=request.user).order_by(
        "-created_at"
    )
    ser = MedicalRecordListSerializer(qs, many=True, context={"request": request})
    return Response(ser.data)


@api_view(["POST"])
@permission_classes([IsActiveVerifiedMedecin])
def revoke_record_access(request, record_id: int):
    record = get_object_or_404(MedicalRecord, id=record_id)

    if record.created_by_id != request.user.id:
        return Response(
            {"detail": "Only owner can revoke"}, status=status.HTTP_403_FORBIDDEN
        )

    ser = RevokeShareSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    doctor_id = ser.validated_data["doctor_id"]

    env = RecordKeyEnvelope.objects.filter(record=record, doctor_id=doctor_id).first()
    if env:
        env.is_active = False
        env.save(update_fields=["is_active"])

    record.allowed_doctors.remove(doctor_id)

    return Response({"detail": "Access revoked", "doctor_id": doctor_id})
