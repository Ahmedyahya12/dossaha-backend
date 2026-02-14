from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from django.utils import timezone

from accounts.models import Role
from common.user_account import User
from .models import MedicalRecord, MedicalDocument, RecordKeyEnvelope
from rest_framework import serializers
from accounts.models import CustomUser, Role

from .models import SecurityEvent


from .models import Referral



class MedicalDocumentUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True)
    document_type = serializers.CharField(required=False)

    encrypted_payload = serializers.CharField()
    payload_iv = serializers.CharField()
    payload_tag = serializers.CharField()

    payload_hash = serializers.CharField()
    signature = serializers.CharField()
    signing_key_fingerprint = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class ReferralCreateSerializer(serializers.Serializer):
    to_doctor_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    encrypted_dek = serializers.CharField()
    key_fingerprint = serializers.CharField(required=False, allow_blank=True, max_length=80)

class ReferralListSerializer(serializers.ModelSerializer):
    record_id = serializers.IntegerField(source="record.id", read_only=True)
    from_doctor_name = serializers.CharField(source="from_doctor.get_full_name", read_only=True)
    to_doctor_name = serializers.CharField(source="to_doctor.get_full_name", read_only=True)

    class Meta:
        model = Referral
        fields = ["id", "record_id", "status", "reason", "created_at", "decided_at",
                  "from_doctor_id", "from_doctor_name", "to_doctor_id", "to_doctor_name"]

class MedicalRecordUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = ["status"]  
         

class SecurityEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    target_doctor_name = serializers.SerializerMethodField()
    doc_title = serializers.CharField(source="doc.title", read_only=True)

    class Meta:
        model = SecurityEvent
        fields = [
            "id",
            "event_type",
            "created_at",
            "actor_name",
            "target_doctor_name",
            "doc_id",
            "doc_title",
            "ip",
        ]

    def get_actor_name(self, obj):
        u = obj.actor
        return (u.get_full_name() or u.email) if u else None

    def get_target_doctor_name(self, obj):
        u = obj.target_doctor
        return (u.get_full_name() or u.email) if u else None


class SharedDoctorSerializer(serializers.ModelSerializer):
    doctor_id = serializers.IntegerField(source="doctor.id", read_only=True)
    doctor_name = serializers.SerializerMethodField()
    doctor_email = serializers.EmailField(source="doctor.email", read_only=True)

    shared_by_id = serializers.IntegerField(source="shared_by.id", read_only=True, allow_null=True)
    shared_by_name = serializers.SerializerMethodField()

    class Meta:
        model = RecordKeyEnvelope
        fields = [
            "doctor_id",
            "doctor_name",
            "doctor_email",
            "shared_by_id",
            "shared_by_name",
            "created_at",
            "is_active",
        ]

    def get_doctor_name(self, obj):
        u = obj.doctor
        if not u:
            return None
        return (u.get_full_name() or u.email)

    def get_shared_by_name(self, obj):
        u = obj.shared_by
        if not u:
            return None
        return (u.get_full_name() or u.email)

class DoctorLookupSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    specialite = serializers.CharField(source="profile.specialite", read_only=True)
    public_key_pem = serializers.CharField(source="profile.public_key_pem", read_only=True)
    key_fingerprint = serializers.CharField(source="profile.key_fingerprint", read_only=True)
    sig_key_fingerprint=serializers.CharField(source="profile.sig_key_fingerprint", read_only=True)
    sig_public_key_pem=serializers.CharField(source="profile.sig_public_key_pem", read_only=True)
    class Meta:
        model = CustomUser
        fields = ["id", "email", "name", "public_key_pem", "key_fingerprint", "sig_key_fingerprint", "sig_public_key_pem","specialite"]

    def get_name(self, obj):
        return obj.get_full_name() or obj.email


class ShareRecordSerializer(serializers.Serializer):
    doctor_email = serializers.EmailField()
    dek_envelope = serializers.DictField()

    def validate_dek_envelope(self, value):
        if "encrypted_dek" not in value:
            raise serializers.ValidationError("encrypted_dek is required")
        # key_fingerprint optional but recommended
        return value

class RevokeShareSerializer(serializers.Serializer):
    doctor_id = serializers.IntegerField()


# sprint 3

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
            "patient_name",   # 
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
