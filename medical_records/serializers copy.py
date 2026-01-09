from rest_framework import serializers
from django.utils import timezone
from .models import MedicalRecord, MedicalDocument, RecordKeyEnvelope


class RecordKeyEnvelopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecordKeyEnvelope
        fields = ["encrypted_dek", "key_fingerprint"]


class MedicalRecordCreateSerializer(serializers.Serializer):
    dek_envelope = RecordKeyEnvelopeSerializer()

    def validate(self, attrs):
        # يمكنك إضافة تحقق: encrypted_dek موجود وlooks like base64
        return attrs


class MedicalRecordListSerializer(serializers.ModelSerializer):
    my_dek_envelope = serializers.SerializerMethodField()

    class Meta:
        model = MedicalRecord
        fields = [
            "id", "patient", "status",
            "created_at", "updated_at",
            "my_dek_envelope",
        ]

    def get_my_dek_envelope(self, obj):
        user = self.context["request"].user
        env = obj.key_envelopes.filter(doctor=user, is_active=True).first()
        if not env:
            return None
        return {"encrypted_dek": env.encrypted_dek, "key_fingerprint": env.key_fingerprint}


class MedicalDocumentCreateSerializer(serializers.Serializer):
    document_type = serializers.CharField()
    title = serializers.CharField(max_length=200)

    encrypted_payload = serializers.CharField()
    payload_iv = serializers.CharField()
    payload_tag = serializers.CharField()

    payload_hash = serializers.CharField()
    signature = serializers.CharField()

    signing_key_fingerprint = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate(self, attrs):
        # تحقق document_type ضمن enum لو تحب:
        return attrs


class MedicalDocumentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalDocument
        fields = [
            "id", "record_id", "document_type", "title",
            "encrypted_payload", "payload_iv", "payload_tag",
            "payload_hash", "signature",
            "signed_by", "signed_at", "signing_key_fingerprint",
            "created_by", "created_at", "is_revoked",
        ]


class MedicalRecordDetailSerializer(serializers.ModelSerializer):
    my_dek_envelope = serializers.SerializerMethodField()
    documents = MedicalDocumentDetailSerializer(many=True)

    class Meta:
        model = MedicalRecord
        fields = [
            "id", "patient", "status",
            "created_by", "created_at", "updated_at",
            "my_dek_envelope",
            "documents",
        ]

    def get_my_dek_envelope(self, obj):
        user = self.context["request"].user
        env = obj.key_envelopes.filter(doctor=user, is_active=True).first()
        if not env:
            return None
        return {"encrypted_dek": env.encrypted_dek, "key_fingerprint": env.key_fingerprint}
