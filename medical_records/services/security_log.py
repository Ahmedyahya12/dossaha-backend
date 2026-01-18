from medical_records.models import SecurityEvent, SecurityEventType

def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

def log_event(*, request, record, event_type, doc=None, target_doctor=None):
    SecurityEvent.objects.create(
        record=record,
        actor=getattr(request, "user", None),
        event_type=event_type,
        doc=doc,
        target_doctor=target_doctor,
        ip=get_client_ip(request) if request else None,
        user_agent=(request.META.get("HTTP_USER_AGENT") if request else None),
    )
