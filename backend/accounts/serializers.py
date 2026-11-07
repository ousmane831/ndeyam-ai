from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from farms.models import Farm, FarmMembership, MembershipRole

from .models import Role

User = get_user_model()


def check_password_strength(password, user=None):
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc
    return password


class MembershipSummarySerializer(serializers.ModelSerializer):
    farm_id = serializers.IntegerField(source="farm.id", read_only=True)
    farm_name = serializers.CharField(source="farm.name", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = FarmMembership
        fields = ["farm_id", "farm_name", "role", "role_label"]


class UserSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "role_label",
            "is_platform_admin",
            "memberships",
            "date_joined",
        ]
        read_only_fields = ["id", "email", "role", "date_joined"]

    @extend_schema_field(MembershipSummarySerializer(many=True))
    def get_memberships(self, user):
        memberships = user.farm_memberships.filter(is_active=True).select_related("farm")
        return MembershipSummarySerializer(memberships, many=True).data


class RegisterSerializer(serializers.Serializer):
    """Inscription publique d'un ÉLEVEUR : crée le compte, son exploitation et l'adhésion propriétaire."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    farm_name = serializers.CharField(max_length=200)
    farm_region = serializers.CharField(max_length=120, required=False, allow_blank=True)
    farm_locality = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un compte existe déjà avec cette adresse e-mail.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Les deux mots de passe ne correspondent pas."}
            )
        candidate = User(email=attrs["email"], first_name=attrs["first_name"], last_name=attrs["last_name"])
        try:
            check_password_strength(attrs["password"], candidate)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"password": exc.detail}) from exc
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            phone=validated_data.get("phone", ""),
            role=Role.ELEVEUR,
        )
        farm = Farm.objects.create(
            name=validated_data["farm_name"],
            region=validated_data.get("farm_region", ""),
            locality=validated_data.get("farm_locality", ""),
            created_by=user,
        )
        FarmMembership.objects.create(farm=farm, user=user, role=MembershipRole.OWNER)
        return user


class LoginSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        "no_active_account": "Adresse e-mail ou mot de passe incorrect, ou compte désactivé.",
    }

    def validate(self, attrs):
        attrs[self.username_field] = attrs.get(self.username_field, "").strip().lower()
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone"]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Le mot de passe actuel est incorrect.")
        return value

    def validate_new_password(self, value):
        return check_password_strength(value, self.context["request"].user)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)


class AdminUserSerializer(serializers.ModelSerializer):
    """Gestion des comptes par un administrateur (création d'experts, changement de rôle, désactivation)."""

    password = serializers.CharField(write_only=True, required=False)
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    farms_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "role_label",
            "is_active",
            "password",
            "farms_count",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "date_joined", "last_login"]

    def validate_email(self, value):
        value = value.strip().lower()
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Un compte existe déjà avec cette adresse e-mail.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Un mot de passe initial est obligatoire."})
        if attrs.get("password"):
            try:
                check_password_strength(attrs["password"], self.instance)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({"password": exc.detail}) from exc
        if self.instance is not None and self.instance.pk == request.user.pk:
            if attrs.get("is_active") is False:
                raise serializers.ValidationError(
                    {"is_active": "Vous ne pouvez pas désactiver votre propre compte."}
                )
            if "role" in attrs and attrs["role"] != Role.ADMIN:
                raise serializers.ValidationError(
                    {"role": "Vous ne pouvez pas retirer votre propre rôle d'administrateur."}
                )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        if user.role == Role.ADMIN:
            user.is_staff = True
            user.save(update_fields=["is_staff"])
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        # L'accès à l'administration Django suit le rôle (un superutilisateur garde son accès).
        instance.is_staff = instance.is_superuser or instance.role == Role.ADMIN
        instance.save()
        return instance
