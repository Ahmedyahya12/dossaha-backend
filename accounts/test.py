
class MedicalRecord(models.Model):

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
        ARCHIVED = "ARCHIVED", "Archived"

 
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="medical_records",
        limit_choices_to={"role": "PATIENT"},
    )


    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_medical_records",
        limit_choices_to={"role": "MEDECIN"},
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MedicalRecord #{self.id} - {self.patient.email}"


class MedicalDocument(models.Model):

    class DocumentType(models.TextChoices):
        LAB = "LAB", "Lab Result"
        XRAY = "XRAY", "X-Ray"
        PRESCRIPTION = "PRESCRIPTION", "Prescription"
        REPORT = "REPORT", "Medical Report"
        OTHER = "OTHER", "Other"

    # 🔹 appartient à un dossier médical
    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    file = models.FileField(upload_to="medical_documents/")

    file_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
    )

   
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_documents",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_type} - Record #{self.medical_record.id}"
    
