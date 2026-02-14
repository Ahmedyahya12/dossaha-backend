from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from .models import Notification
from .serializers import NotificationSerializer

class NotifPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_notifications(request):
    qs = Notification.objects.filter(recipient=request.user).order_by("-created_at")
    paginator = NotifPagination()
    page = paginator.paginate_queryset(qs, request)
    ser = NotificationSerializer(page, many=True)
    return paginator.get_paginated_response(ser.data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def unread_count(request):
    n = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return Response({"unread": n}, status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_read(request, notif_id: int):
    notif = Notification.objects.filter(id=notif_id, recipient=request.user).first()
    if not notif:
        return Response({"detail": "Notification introuvable."}, status=status.HTTP_404_NOT_FOUND)
    notif.is_read = True
    notif.save(update_fields=["is_read"])
    return Response({"detail": "OK"}, status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return Response({"detail": "OK"}, status=status.HTTP_200_OK)