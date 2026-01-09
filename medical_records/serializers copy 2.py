from rest_framework import serializers
from accounts.serializers import UserInfoSerializer
from medical_records.models import MedicalDocument, MedicalRecord


class MedicalRecordSerializer(serializers.ModelSerializer):
    # diagnosis
    # medical_history
    patient = UserInfoSerializer(read_only=True)
    created_by = UserInfoSerializer(read_only=True)

    class Meta:
        model = MedicalRecord
        fields = "__all__"
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentUploadSerializer(serializers.Serializer):
    """
    Serializer pour l'upload de documents
    """
    file = serializers.FileField()
    record_id = serializers.IntegerField()
    
    def validate_file(self, value):
        """Valide le type et la taille du fichier"""
        # Limite à 10MB
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Fichier trop volumineux (max 10MB)")
        
        # Types autorisés
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Type de fichier non autorisé")
        
        return value

class MedicalDocumentSerializer(serializers.ModelSerializer):
    # medical_record=serializers.SerializerMethodField()
    
    class Meta:
        model = MedicalDocument
        fields = "__all__"
        read_only_fields = ['id', 'uploaded_at']
