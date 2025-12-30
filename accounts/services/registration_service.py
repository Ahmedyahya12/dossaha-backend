from datetime import timedelta
from rest_framework import serializers
from common.user_account import User
from django.utils.crypto import get_random_string
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone


def validate_registration_data(serializer):
    if not serializer.is_valid():
        raise serializers.ValidationError(serializer.errors)
    email = serializer.validated_data["email"]
    if User.objects.filter(email=email).exists():
        raise serializers.ValidationError({"email": "Email already exist"})

    return email


# create user


def create_medecin(serializer):
    return serializer.save(is_active=False)


def create_profile(user, data):
    profile = user.profile
    profile.specialite = data.get("specialite")
    profile.licence_number = data.get("licence_number")
    profile.telephone = data.get("telephone")
    profile.bio = data.get("bio")
    profile.save()


def generate_and_save_activation_token(user):
    token = get_random_string(40)
    expire_date = timezone.now() + timedelta(days=1)

    user.profile.activation_token = token
    user.profile.activation_token_expire = expire_date
    user.profile.save()

    return token


def build_activation_link(token):

    return f"{settings.BASE_URL}/api/accounts/activate/{token}/"


def send_activation_email(user, activation_link):
    subject = "Activez votre compte DOSSAHA - Plateforme médicale sécurisée"

    # Contenu HTML
    html_content = render_to_string(
        "emails/activation_email.html",
        {
            "activation_link": activation_link,
            "logo_url": "https://res.cloudinary.com/dc8znovuu/image/upload/v1767099463/health-report_htnuvu.png",
            "platform_name": "DOSSAHA",
            "user_name": f"{user.first_name} {user.last_name}",
            # 'user_role': user.role  # 'medecin' ou 'patient'
            "user_role": "medecin",  #
        },
    )

    # Version texte alternative
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject, text_content, settings.EMAIL_HOST_USER, [user.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


def send_email_to_medecin(user, activation_link):
    send_activation_email(user, activation_link)
