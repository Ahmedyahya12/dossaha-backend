import base64
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from common.user_account import User
from medical_records.models import MedicalDocument, MedicalRecord
from .serializers import (
    DocumentUploadSerializer,
    MedicalDocumentSerializer,
    MedicalRecordSerializer,
)
from django.shortcuts import get_object_or_404
from rest_framework.serializers import ValidationError
from rest_framework import status


#  List Recods
@api_view(["GET"])
def list_recods(request):
    records = MedicalRecord.objects.all()
    serializer = MedicalRecordSerializer(records, many=True)
    return Response(serializer.data)


# Get Record
@api_view(["GET"])
def get_recod(request, pk):
    record = get_object_or_404(MedicalRecord, id=pk)
    serializer = MedicalRecordSerializer(record)
    return Response(serializer.data)


# Create Record
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_record(request):
    patient_id = request.data.get("patient")

    serializer = MedicalRecordSerializer(data={})
    serializer.is_valid(raise_exception=True)
    
    serializer.save(
        created_by=request.user, patient_id=patient_id, status="OPEN"  # instance  # id
    )

    return Response(serializer.data, status=status.HTTP_201_CREATED)


# # Archive Record
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def archive_record(request, pk):
    medicalrecord = get_object_or_404(MedicalRecord, pk=pk)
    medicalrecord.status = MedicalRecord.Status.ARCHIVED
    medicalrecord.save()
    serializer = MedicalRecordSerializer(medicalrecord)
    return Response(serializer.data)


# Update Record
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_record(request, pk):
    medicalrecord = get_object_or_404(MedicalRecord, id=pk)
    data = request.data
    serializer = MedicalRecordSerializer(medicalrecord, data=data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_medical_documents(request, record_pk):
    medical_documents = MedicalDocument.objects.filter(medical_record=record_pk)
    serializer = MedicalDocumentSerializer(medical_documents, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_medical_document(request, record_pk, pk):
    medical_record = get_object_or_404(MedicalRecord, id=record_pk)
    medical_document = get_object_or_404(
        MedicalDocument, id=pk, medical_record=medical_record
    )
    serializer = MedicalDocumentSerializer(medical_document)
    return Response(serializer.data)


@api_view(["GET"])
# @permission_classes([IsAuthenticated])
def view_medical_document(request, record_pk, pk):
    """
    Affiche un document médical DÉCHIFFRÉ dans le navigateur
    (au lieu de le télécharger)

    Utile pour les PDF, images, etc.

    Endpoint: GET /api/medicalrecord/records/{record_pk}/documents/{pk}/view/
    """
    print(f" Visualisation du document #{pk} du record #{record_pk}")

    # 1. Récupère le record et le document
    medical_record = get_object_or_404(MedicalRecord, id=record_pk)
    medical_document = get_object_or_404(
        MedicalDocument, id=pk, medical_record=medical_record
    )

    try:
        # 2. Déchiffre le fichier
        print(f"    Déchiffrement du fichier...")
        decrypted_content = medical_document.get_decrypted_file()
        print(f"    Fichier déchiffré: {len(decrypted_content)} bytes")

        # 3. Prépare la réponse HTTP (inline au lieu d'attachment)
        response = HttpResponse(
            decrypted_content,
            content_type=medical_document.file_type or "application/octet-stream",
        )

        # 4. "inline" = affiche dans le navigateur au lieu de télécharger
        response["Content-Disposition"] = (
            f'inline; filename="{medical_document.file_name}"'
        )
        response["Content-Length"] = len(decrypted_content)

       
        return response

    except Exception as e:
        
        return Response(
            {"error": f"Erreur lors du déchiffrement: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_medical_document(request):
    data = request.data

    record = get_object_or_404(MedicalRecord, id=data["medical_record"])
    serializer = DocumentUploadSerializer(
        data={"file": request.FILES.get("file"), "record_id": data["medical_record"]}
    )
    serializer.is_valid(raise_exception=True)

    uploaded_file = serializer.validated_data["file"]

    file_content = uploaded_file.read()

    document = MedicalDocument(
        medical_record=record,
        file_name=uploaded_file.name,
        file_type=uploaded_file.content_type,
        file_size=uploaded_file.size,
        uploaded_by=request.user,
    )
    document.save_encrypted_file(file_content)

    return Response(
        MedicalDocumentSerializer(document).data, status=status.HTTP_201_CREATED
    )


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_medical_document(request, record_pk, pk):
    medical_document = get_object_or_404(
        MedicalDocument, id=pk, medical_record=record_pk
    )
    serializer = MedicalDocumentSerializer(medical_document, data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(uploaded_by=request.user)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_medical_document(request, record_pk, pk):
    """
    Télécharge le fichier DÉCHIFFRÉ (binaire).

    Retourne le fichier directement (pas en JSON).
    Le navigateur télécharge automatiquement.

    USAGE:
    - Bouton "Télécharger" dans l'interface
    - Lien direct: <a href="/api/.../download/">Télécharger</a>

    REACT:
    - window.open(url) ou fetch() avec blob

    Endpoint: GET /api/records/{record_pk}/documents/{pk}/download/
    """
    medical_record = get_object_or_404(MedicalRecord, id=record_pk)
    medical_document = get_object_or_404(
        MedicalDocument, id=pk, medical_record=medical_record
    )

    try:
        # Déchiffre le fichier
        decrypted_content = medical_document.get_decrypted_file()

        # Retourne le fichier binaire
        response = HttpResponse(
            decrypted_content,
            content_type=medical_document.file_type or "application/octet-stream",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{medical_document.file_name}"'
        )
        response["Content-Length"] = len(decrypted_content)

        return response

    except Exception as e:
        return Response(
            {"error": f"Erreur lors du déchiffrement: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
