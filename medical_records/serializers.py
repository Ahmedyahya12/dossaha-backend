from rest_framework import serializers
from accounts.serializers import UserInfoSerializer
from medical_records.models import MedicalRecord


class MedicalRecordSerializer(serializers.ModelSerializer):
    patient = UserInfoSerializer(read_only=True)
    created_by = UserInfoSerializer(read_only=True)

    class Meta:
        model = MedicalRecord
        fields = "__all__"
     