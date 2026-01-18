from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver


from .managers import CustomUserManager

from django.conf import settings
from django.db import models


class PatientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_patients",
        limit_choices_to={"role": "MEDECIN"},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PatientProfile({self.user.email})"


class Specialite(models.TextChoices):
    GENERALISTE = "GENERALISTE", "Médecine générale"
    PEDIATRIE = "PEDIATRIE", "Pédiatrie"
    GYNECO = "GYNECO", "Gynécologie-Obstétrique"
    CARDIO = "CARDIO", "Cardiologie"
    DERMATO = "DERMATO", "Dermatologie"
    OPHTALMO = "OPHTALMO", "Ophtalmologie"
    ORL = "ORL", "ORL"
    URGENCE = "URGENCE", "Médecine d'urgence"
    RADIO = "RADIO", "Radiologie"
    CHIR = "CHIR", "Chirurgie générale"
    
    
class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    MEDECIN = "MEDECIN", "Medecin"
    PATIENT = "PATIENT", "Patient"


class CustomUser(AbstractUser):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("ACTIVE", "Active"),
        ("REJECTED", "Rejected"),
    )

    username = None

    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=20, choices=Role.choices, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return f'{self.email} # {self.id}'


class MedecinProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # Activation email (OK )
    activation_token = models.CharField(max_length=80, blank=True, null=True)
    activation_token_expire = models.DateTimeField(null=True, blank=True)

    # Vérification admin
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_medecins",
        limit_choices_to={"role": "ADMIN"},
    )

    # Identité pro
    specialite = models.CharField(max_length=30, choices=Specialite.choices, null=True, blank=True)
    licence_number = models.CharField(max_length=50, null=True, blank=True)
    organisation = models.CharField(max_length=120, null=True, blank=True)   # hôpital/clinique
    telephone = models.CharField(max_length=20, blank=True, null=True)
    photo = models.ImageField(upload_to="medecins/", blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    # Crypto identity ( pour E2EE + signature)
    public_key_pem = models.TextField(null=True, blank=True)   # clé publique RSA/EC en PEM
    key_fingerprint = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    key_uploaded_at = models.DateTimeField(null=True, blank=True)

    sig_public_key_pem = models.TextField(null=True, blank=True)
    sig_key_fingerprint = models.CharField(max_length=80, null=True, blank=True, db_index=True)

    sig_key_uploaded_at = models.DateTimeField(null=True, blank=True)

    
    def __str__(self):
        return self.user.email



@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created and instance.role == "MEDECIN":
        MedecinProfile.objects.get_or_create(user=instance)