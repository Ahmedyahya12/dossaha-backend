from rest_framework import serializers
from accounts.models import CustomUser, MedecinProfile

from rest_framework import serializers


from rest_framework import serializers
from accounts.models import CustomUser, Role, PatientProfile

class PatientListSerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ["id", "code", "email", "full_name", "first_name", "last_name", "created_at"]

    def get_code(self, obj):
        return f"PAT-{str(obj.id).zfill(4)}"

    def get_full_name(self, obj):
        name = (obj.get_full_name() or "").strip()
        return name if name else None


class PatientCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    email = serializers.EmailField()

    def validate_email(self, v):
        v = v.strip().lower()
        if CustomUser.objects.filter(email=v).exists():
            raise serializers.ValidationError("Email already exists")
        return v



class SigningKeyUploadSerializer(serializers.Serializer):
    sig_public_key_pem = serializers.CharField()
    sig_key_fingerprint = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_sig_public_key_pem(self, v: str):
        v = (v or "").strip()
        if "BEGIN PUBLIC KEY" not in v:
            raise serializers.ValidationError("Invalid PEM public key")
        return v

    def validate_sig_key_fingerprint(self, v):
        if v is None:
            return None
        v = str(v).strip()
        if v and not v.startswith("sha256:"):
            raise serializers.ValidationError("Fingerprint must start with sha256:")
        return v



    

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
