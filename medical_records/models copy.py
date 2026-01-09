from django.db import models
from django.conf import settings
from .encryption import EncryptionService


class MedicalRecord(models.Model):

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
        ARCHIVED = "ARCHIVED", "Archived"

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
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_medical_records",
        limit_choices_to={"role": "MEDECIN"},
    )
    encrypted_record_key = models.BinaryField(
        null=True, blank=True, help_text="Clé du record chiffrée avec la Master Key"
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        """
        Override save pour générer et chiffrer la clé du record
        """
        # CORRECTION: Vérifier explicitement si None ou vide
        if self.encrypted_record_key is None or len(self.encrypted_record_key or b'') == 0:
            print(" Génération de la clé du record...")  # Debug
            
            # 1. Génère une nouvelle clé pour ce record
            record_key = EncryptionService.generate_record_key()
            # print(f"    Clé générée: {len(record_key)} bytes")
            
            # 2. Chiffre cette clé avec la Master Key
            self.encrypted_record_key = EncryptionService.encrypt_record_key(record_key)
            # print(f"   Clé chiffrée: {len(self.encrypted_record_key)} bytes")
        else:
            print(" Clé existante trouvée")
        
        super().save(*args, **kwargs)
    
    def get_decrypted_record_key(self):
        """
        Déchiffre et retourne la clé du record
        À utiliser uniquement côté serveur
        """
        #  Vérification explicite
        if self.encrypted_record_key is None:
            raise ValueError(
                f" MedicalRecord #{self.id} n'a pas de clé chiffrée!\n"
                f"   Le record a été créé sans encryption.\n"
                f"   Solution: Supprime ce record et recrée-le."
            )
        
        # S'assurer que c'est en bytes avant de décrypter
        encrypted_key = self.encrypted_record_key
        if isinstance(encrypted_key, memoryview):
            encrypted_key = bytes(encrypted_key)
        
        return EncryptionService.decrypt_record_key(encrypted_key)

    def __str__(self):
        return f"MedicalRecord #{self.id}"


class MedicalDocument(models.Model):

    class DocumentType(models.TextChoices):
        LAB = "LAB", "Lab Result"
        XRAY = "XRAY", "X-Ray"
        PRESCRIPTION = "PRESCRIPTION", "Prescription"
        REPORT = "REPORT", "Medical Report"
        OTHER = "OTHER", "Other"

    medical_record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    file = models.FileField(upload_to="medical_documents/", null=True, blank=True)
    encrypted_file = models.BinaryField(
        help_text="Fichier chiffré avec la clé du record",
        null=True,blank=True
    )

    file_name = models.CharField(max_length=255,null=True,blank=True)
    file_type = models.CharField(max_length=50,null=True,blank=True)  # ex: "application/pdf"
    file_size = models.IntegerField(null=True,blank=True)  # taille en bytes

    file_type = models.CharField(
        max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
     
    def save_encrypted_file(self, file_content):
        """
        Chiffre et sauvegarde un fichier
        
        Args:
            file_content (bytes): Contenu du fichier en clair
        """
        print(f" Chiffrement du fichier {self.file_name}...")
        
        # 1. Récupère la clé du record (déchiffrée)
        record_key = self.medical_record.get_decrypted_record_key()
        print(f"   Clé du record récupérée")
        
        # 2. Chiffre le fichier avec cette clé
        self.encrypted_file = EncryptionService.encrypt_file(file_content, record_key)
        print(f"   Fichier chiffré: {len(self.encrypted_file)} bytes")
        
        self.save()
        print(f"   Document sauvegardé en DB")
    
    def get_decrypted_file(self):
        """
        Déchiffre et retourne le fichier
        
        Returns:
            bytes: Contenu du fichier en clair
        """
        # 1. Récupère la clé du record (déchiffrée)
        record_key = self.medical_record.get_decrypted_record_key()
        
        # 2. Convertir memoryview si nécessaire
        encrypted_file = self.encrypted_file
        if isinstance(encrypted_file, memoryview):
            encrypted_file = bytes(encrypted_file)
        
        # 3. Déchiffre le fichier
        return EncryptionService.decrypt_file(encrypted_file, record_key)
    
    def __str__(self):
        return f"{self.file_name} #{self.id} - Record #{self.medical_record.id}"