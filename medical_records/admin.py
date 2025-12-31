from django.contrib import admin

from medical_records.models import MedicalDocument, MedicalRecord

admin.site.register([MedicalRecord,MedicalDocument])