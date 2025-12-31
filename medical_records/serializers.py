from rest_framework import serializers
from accounts.serializers import UserInfoSerializer
from medical_records.models import MedicalDocument, MedicalRecord


class MedicalRecordSerializer(serializers.ModelSerializer):
    patient = UserInfoSerializer(read_only=True)
    created_by = UserInfoSerializer(read_only=True)

    class Meta:
        model = MedicalRecord
        fields = "__all__"


class MedicalDocumentSerializer(serializers.ModelSerializer):
    # medical_record=serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalDocument
        fields = "__all__"
