from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from .models import MedicalRecord, MedicalDocument, RecordKeyEnvelope
from .serializers import (
    MedicalRecordCreateSerializer,
    MedicalRecordListSerializer,
    MedicalRecordDetailSerializer,
    MedicalDocumentCreateSerializer,
    MedicalDocumentDetailSerializer,
)
from .permissions import IsActiveVerifiedMedecin


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
    record = MedicalRecord.objects.get(id=record_id)

    if not _can_access_record(request.user, record):
        return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

    has_env = record.key_envelopes.filter(doctor=request.user, is_active=True).exists()
    if not has_env:
        return Response({"detail": "No active DEK envelope"}, status=status.HTTP_403_FORBIDDEN)

    doc = MedicalDocument.objects.get(id=doc_id, record=record)

    return Response({
        "id": doc.id,
        "record_id": record.id,
        "encrypted_payload": doc.encrypted_payload,
        "payload_iv": doc.payload_iv,
        "payload_tag": doc.payload_tag,
        "payload_hash": doc.payload_hash,
        "signature": doc.signature,
        "signed_by": doc.signed_by_id,
        "signed_at": doc.signed_at,
        "signing_key_fingerprint": doc.signing_key_fingerprint,
    })