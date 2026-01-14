from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from django.utils import timezone

from accounts.models import Role
from common.user_account import User
from .models import MedicalRecord, MedicalDocument, RecordKeyEnvelope


class RecordKeyEnvelopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecordKeyEnvelope
        fields = ["encrypted_dek", "key_fingerprint"]


class MedicalRecordCreateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(min_value=1)
    dek_envelope = RecordKeyEnvelopeSerializer()

    def validate_patient_id(self, value):
        patient = get_object_or_404(User, id=value, role=Role.PATIENT)
        return value

    def validate(self, attrs):
        patient = User.objects.get(id=attrs["patient_id"])
        attrs["patient"] = patient
        return attrs

class MedicalRecordListSerializer(serializers.ModelSerializer):
    patient_id = serializers.IntegerField(source="patient.id", read_only=True)

    my_dek_envelope = serializers.SerializerMethodField()
    documents_count = serializers.SerializerMethodField()
    access = serializers.SerializerMethodField()

    class Meta:
        model = MedicalRecord
        fields = [
            "id",
            "patient_id",
            "status",
            "created_at",
            "updated_at",
            "documents_count",
            "access",
            "my_dek_envelope",
        ]

    def get_my_dek_envelope(self, obj):
        user = self.context["request"].user
        env = obj.key_envelopes.filter(doctor=user, is_active=True).first()
        if not env:
            return None
        return {
            "encrypted_dek": env.encrypted_dek,
            "key_fingerprint": env.key_fingerprint,
        }

    def get_documents_count(self, obj):
        return obj.documents.count()

    def get_access(self, obj):
        user = self.context["request"].user
        return "OWNER" if obj.created_by_id == user.id else "SHARED"


class MedicalDocumentCreateSerializer(serializers.Serializer):
    document_type = serializers.CharField()
    title = serializers.CharField(max_length=200)

    encrypted_payload = serializers.CharField()
    payload_iv = serializers.CharField()
    payload_tag = serializers.CharField()

    payload_hash = serializers.CharField()
    signature = serializers.CharField()

    signing_key_fingerprint = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    def validate(self, attrs):
        return attrs


class MedicalDocumentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalDocument
        fields = [
            "id",
            "record_id",
            "document_type",
            "title",
            "encrypted_payload",
            "payload_iv",
            "payload_tag",
            "payload_hash",
            "signature",
            "signed_by",
            "signed_at",
            "signing_key_fingerprint",
            "created_by",
            "created_at",
            "is_revoked",
        ]
    def get_signed_by(self, obj):
        if not obj.signed_by:
            return None
        return {
            "id": obj.signed_by.id,
            "name": obj.signed_by.get_full_name()
                    or obj.signed_by.email
        }

    def get_created_by(self, obj):
        if not obj.created_by:
            return None
        return {
            "id": obj.created_by.id,
            "name": obj.created_by.get_full_name()
                    or obj.created_by.email
        }


class MedicalDocumentMetaSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MedicalDocument
        fields = [
            "id",
            "document_type",
            "title",
            "created_by_name",   # 
            "created_at",
            "is_revoked",
        ]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        # الاسم الكامل إن وجد، وإلا الإيميل
        return obj.created_by.get_full_name() or obj.created_by.email

class MedicalRecordDetailSerializer(serializers.ModelSerializer):
    patient_id = serializers.IntegerField(source="patient.id", read_only=True)
    patient_name = serializers.SerializerMethodField()

    my_dek_envelope = serializers.SerializerMethodField()
    documents = MedicalDocumentMetaSerializer(many=True)

    class Meta:
        model = MedicalRecord
        fields = [
            "id",
            "patient_id",
            "patient_name",   # ✅ الجديد
            "status",
            "created_by",
            "created_at",
            "updated_at",
            "my_dek_envelope",
            "documents",
        ]

    def get_patient_name(self, obj):
        """
        Return patient's display name for UI (non-sensitive).
        Priority:
        - full name
        - email
        - fallback
        """
        patient = obj.patient
        if not patient:
            return None

        full_name = patient.get_full_name()
        if full_name:
            return full_name

        return patient.email  # fallback

    def get_my_dek_envelope(self, obj):
        user = self.context["request"].user
        env = obj.key_envelopes.filter(doctor=user, is_active=True).first()
        if not env:
            return None
        return {
            "encrypted_dek": env.encrypted_dek,
            "key_fingerprint": env.key_fingerprint,
        }
