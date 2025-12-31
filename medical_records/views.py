from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from common.user_account import User
from medical_records.models import MedicalDocument, MedicalRecord
from .serializers import MedicalDocumentSerializer, MedicalRecordSerializer
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_medical_document(request):
    data=request.data 
    serializer = MedicalDocumentSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    serializer.save(uploaded_by=request.user)
    return Response(serializer.data)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_medical_document(request,record_pk, pk):
    medical_document = get_object_or_404(
        MedicalDocument, id=pk, medical_record=record_pk
    )
    serializer = MedicalDocumentSerializer(medical_document,data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(uploaded_by=request.user)
    return Response(serializer.data)
