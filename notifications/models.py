from django.conf import settings
from django.db import models

class NotificationType(models.TextChoices):
    RECORD_SHARED = "RECORD_SHARED", "Dossier partagé"
    REFERRAL_CREATED = "REFERRAL_CREATED", "Referral reçu"
    REFERRAL_ACCEPTED = "REFERRAL_ACCEPTED", "Referral accepté"
    REFERRAL_REJECTED = "REFERRAL_REJECTED", "Referral refusé"
    ACCESS_REVOKED = "ACCESS_REVOKED", "Accès révoqué"

class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=40, choices=NotificationType.choices)
    title = models.CharField(max_length=120)
    message = models.TextField(blank=True)

    # liens utiles
    record_id = models.IntegerField(null=True, blank=True)
    referral_id = models.IntegerField(null=True, blank=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.recipient_id} - {self.type} - {self.title}"