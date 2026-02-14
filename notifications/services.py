# notifications/services.py
from django.db.utils import OperationalError, ProgrammingError
from notifications.models import Notification

def notify(recipient, type, title, message, record_id=None, referral_id=None):
    try:
        Notification.objects.create(
            recipient=recipient,
            type=type,
            title=title,
            message=message,
            record_id=record_id,
            referral_id=referral_id,
        )
    except (OperationalError, ProgrammingError):
        # ✅ fallback : ne casse pas l'API si la table n'existe pas encore
        # tu peux logguer ici si tu veux
        return None