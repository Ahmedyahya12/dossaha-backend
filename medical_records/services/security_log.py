# medical_records/services/security.py (مثال)

from medical_records.models import SecurityEvent


def log_event(*, record, actor=None, event_type, doc=None, target_doctor=None, request=None):
    ip = None
    ua = None
    if request is not None:
        ip = request.META.get("REMOTE_ADDR")
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:255]

    return SecurityEvent.objects.create(
        record=record,
        actor=actor,
        event_type=event_type,
        doc=doc,
        target_doctor=target_doctor,
        ip=ip,
        user_agent=ua,
    )
