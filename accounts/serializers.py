from rest_framework import serializers
from accounts.models import CustomUser, MedecinProfile


class MedecinProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedecinProfile
        fields = [
            "specialite",
            "licence_number",
            "organisation",
            "telephone",
            "photo",
            "bio",
            "public_key_pem",
            "key_fingerprint",
            "key_uploaded_at",
            "is_verified",
            "verified_at",
        ]


class CurrentUserSerializer(serializers.ModelSerializer):
    profile = MedecinProfileSerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "status",
            "is_email_verified",
            "created_at",
            "profile",
        ]


class SignUpSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "email", "password"]
        extra_kwargs = {
            "first_name": {"required": True, "allow_blank": False},
            "last_name": {"required": True, "allow_blank": False},
            "email": {"required": True, "allow_blank": False},
            "password": {
                "write_only": True,
                "required": True,
                "min_length": 8,
                "allow_blank": False,
            },
        }

    def create(self, validated_data):

        user = CustomUser(
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            email=validated_data["email"],
        )
        user.set_password(validated_data["password"])
        user.save()

        return user


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("id", "email", "first_name", "last_name")
