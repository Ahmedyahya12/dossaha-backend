from django.conf import settings
from django.db import models
from django.utils import timezone


class RecordStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    CLOSED = "CLOSED", "Closed"
    ARCHIVED = "ARCHIVED", "Archived"


class DocumentType(models.TextChoices):
    CONSULT_NOTE = "CONSULT_NOTE", "Consultation"
    PRESCRIPTION = "PRESCRIPTION", "Prescription"
    LAB_RESULT = "LAB_RESULT", "Lab Result"
    IMAGING_REPORT = "IMAGING_REPORT", "Imaging Report"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY", "Discharge Summary"


class MedicalRecord(models.Model):
    """
    dossier = metadata
    """

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medical_records",
        limit_choices_to={"role": "PATIENT"},
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        
        related_name="created_records",
        limit_choices_to={"role": "MEDECIN"},
    )

    status = models.CharField(
        max_length=10,
        choices=RecordStatus.choices,
        default=RecordStatus.OPEN,
    )

    version = models.PositiveIntegerField(default=1)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    # Permissions
    allowed_doctors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="shared_records",
        limit_choices_to={"role": "MEDECIN"},
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def touch_access(self):
        self.last_accessed_at = timezone.now()
        self.save(update_fields=["last_accessed_at"])

    def __str__(self):
        return f"Record#{self.id} patient={self.patient}"


class RecordKeyEnvelope(models.Model):

    record = models.ForeignKey(
        MedicalRecord, on_delete=models.CASCADE, related_name="key_envelopes"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        related_name="record_key_envelopes",
        limit_choices_to={"role": "MEDECIN"},
    )

    encrypted_dek = models.TextField(null=True)  # Base64 RSA-encrypted DEK
    key_fingerprint = models.CharField(
        max_length=80, null=True, blank=True
    )  # e.g. sha256:...
    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)  # revocation

    class Meta:
        unique_together = ("record", "doctor")

    def __str__(self):
        return f"Envelope record={self.record_id} doctor={self.doctor_id}"


class MedicalDocument(models.Model):
    record = models.ForeignKey(
        MedicalRecord, on_delete=models.CASCADE, related_name="documents"
    )

    document_type = models.CharField(max_length=30, choices=DocumentType.choices, default=DocumentType.CONSULT_NOTE)
    title = models.CharField(max_length=200,null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_documents",
        limit_choices_to={"role": "MEDECIN"},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # E2EE: encrypted payload (AES-GCM)
    encrypted_payload = models.TextField(null=True)  # Base64 ciphertext
    payload_iv = models.CharField(max_length=64, null=True)  # Base64 nonce/iv
    payload_tag = models.CharField(max_length=64, null=True)  # Base64 gcm tag

    # Integrity & signature
    payload_hash = models.CharField(max_length=128, null=True)  # sha256 hex or base64
    signature = models.TextField(null=True)  # Base64 signature
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name="signed_documents",
        limit_choices_to={"role": "MEDECIN"},
    )
    signed_at = models.DateTimeField(null=True)

    signing_key_fingerprint = models.CharField(max_length=80, null=True, blank=True)

    is_revoked = models.BooleanField(default=False)

    def __str__(self):
        return f"Doc#{self.id} record={self.record_id}"
