from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver


from .managers import CustomUserManager


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
    role = models.CharField(max_length=20, choices=Role.choices, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class MedecinProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        # limit_choices_to={"role": "MEDECIN"},
    )

    activation_token = models.CharField(max_length=50, blank=True, null=True)
    activation_token_expire = models.DateTimeField(null=True, blank=True)

    is_verified = models.BooleanField(default=False)
    specialite = models.CharField(max_length=100, blank=True, null=True)

    licence_number = models.CharField(max_length=50, blank=True, null=True)

    photo = models.ImageField(upload_to="medecins/", blank=True, null=True)

    bio = models.TextField(blank=True, null=True)

    telephone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Dr {self.user.first_name}  {self.user.last_name}"



@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, **kwargs):

    if instance.role == "MEDECIN":
        if not hasattr(instance, "profile"):
            MedecinProfile.objects.create(user=instance)
