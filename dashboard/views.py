# dashboard/views.py
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from medical_records.models import MedicalRecord, MedicalDocument
from accounts.models import Role
from medical_records.permissions import IsActiveVerifiedMedecin


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsActiveVerifiedMedecin])
def medical_dashboard_stats(request):
    user = request.user

    # dossiers visibles par ce médecin (owner + shared)
    records_qs = MedicalRecord.objects.filter(
        # owner
        created_by=user
    ).union(
        MedicalRecord.objects.filter(allowed_doctors=user)
    )

    # IMPORTANT: union retourne queryset spécial — الأفضل نعمل list ids
    record_ids = list(records_qs.values_list("id", flat=True))

    # documents داخل هذه dossiers فقط
    docs_qs = MedicalDocument.objects.filter(record_id__in=record_ids)

    now = timezone.now()
    last_7 = now - timedelta(days=7)
    last_14 = now - timedelta(days=14)

    total_records = len(record_ids)
    open_records = MedicalRecord.objects.filter(id__in=record_ids, status="OPEN").count()

    total_documents = docs_qs.count()
    docs_last_7_days = docs_qs.filter(created_at__gte=last_7).count()

    docs_by_type = (
        docs_qs.values("document_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    activity_last_14_days = (
        docs_qs.filter(created_at__gte=last_14)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )

    return Response({
        "total_records": total_records,
        "open_records": open_records,
        "total_documents": total_documents,
        "docs_last_7_days": docs_last_7_days,
        "docs_by_type": list(docs_by_type),
        "activity_last_14_days": list(activity_last_14_days),
    })
