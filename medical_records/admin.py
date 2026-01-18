from django.contrib import admin

from medical_records.models import MedicalDocument, MedicalRecord, RecordKeyEnvelope, SecurityEvent

admin.site.register([MedicalRecord,MedicalDocument,RecordKeyEnvelope])


admin.site.register(SecurityEvent)