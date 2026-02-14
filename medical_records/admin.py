from django.contrib import admin

from medical_records.models import MedicalDocument, MedicalRecord, RecordKeyEnvelope, Referral, SecurityEvent

admin.site.register([MedicalRecord,MedicalDocument,RecordKeyEnvelope,Referral])


admin.site.register(SecurityEvent)