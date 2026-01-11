from django.contrib import admin

from medical_records.models import MedicalDocument, MedicalRecord, RecordKeyEnvelope

admin.site.register([MedicalRecord,MedicalDocument,RecordKeyEnvelope])