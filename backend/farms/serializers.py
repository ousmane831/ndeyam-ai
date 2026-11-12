from django.contrib.auth import get_user_model
from rest_framework import serializers

from accounts.models import Role

from .access import membership_for
from .models import Farm, FarmMembership, MembershipRole

User = get_user_model()


class FarmSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()
    my_role_label = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Farm
        fields = [
            "id",
            "name",
            "country",
            "region",
            "locality",
            "description",
            "is_active",
            "is_demo",
            "my_role",
            "my_role_label",
            "members_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_demo", "created_at", "updated_at"]

    def _membership(self, farm):
        cache = self.context.setdefault("_membership_cache", {})
        if farm.pk not in cache:
            cache[farm.pk] = membership_for(self.context["request"].user, farm)
        return cache[farm.pk]

    def get_my_role(self, farm) -> str | None:
        membership = self._membership(farm)
        return membership.role if membership else None

    def get_my_role_label(self, farm) -> str | None:
        membership = self._membership(farm)
        return membership.get_role_display() if membership else None

    def get_members_count(self, farm) -> int:
        return farm.memberships.filter(is_active=True).count()

    def validate_country(self, value):
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError("Indiquez le code pays à deux lettres (ex. SN).")
        return value


class FarmMemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True, required=False)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_role = serializers.CharField(source="user.role", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = FarmMembership
        fields = [
            "id",
            "email",
            "user_id",
            "user_email",
            "user_name",
            "user_role",
            "role",
            "role_label",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_role(self, value):
        if value == MembershipRole.OWNER:
            raise serializers.ValidationError("Le rôle de propriétaire ne peut pas être attribué ici.")
        return value

    def validate(self, attrs):
        farm = self.context["farm"]
        if self.instance is None:
            email = (attrs.pop("email", "") or "").strip().lower()
            if not email:
                raise serializers.ValidationError({"email": "L'adresse e-mail du membre est obligatoire."})
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user is None:
                raise serializers.ValidationError(
                    {
                        "email": (
                            "Aucun compte actif ne correspond à cette adresse. "
                            "La personne doit d'abord s'inscrire."
                        )
                    }
                )
            if FarmMembership.objects.filter(farm=farm, user=user).exists():
                raise serializers.ValidationError(
                    {"email": "Cette personne est déjà membre de l'exploitation."}
                )
            attrs["user"] = user
        else:
            if self.instance.role == MembershipRole.OWNER:
                raise serializers.ValidationError(
                    "Le propriétaire de l'exploitation ne peut pas être modifié ici."
                )
            attrs.pop("email", None)
            user = self.instance.user

        role = attrs.get("role", getattr(self.instance, "role", None))
        if role is None:
            raise serializers.ValidationError({"role": "Le rôle est obligatoire."})
        if role in (MembershipRole.EXPERT, MembershipRole.VETERINARIAN) and user.role != Role.EXPERT:
            raise serializers.ValidationError(
                {
                    "role": (
                        "Seul un compte de type Expert peut être invité comme nutritionniste ou vétérinaire."
                    )
                }
            )
        if role == MembershipRole.MANAGER and user.role == Role.EXPERT:
            raise serializers.ValidationError(
                {"role": "Un compte Expert ne peut pas être gestionnaire : invitez-le comme spécialiste."}
            )
        return attrs
