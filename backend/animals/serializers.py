from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.serializers import FarmScopedRelatedField, ModelCleanMixin, WritableFarmField

from .models import (
    Animal,
    AnimalCategory,
    AnimalGroup,
    AnimalObservation,
    Breed,
    PhysiologicalStage,
    ProductionObjective,
    Species,
)

# --- Nomenclatures ---------------------------------------------------------------------


class SpeciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Species
        fields = ["id", "code", "name", "scientific_name", "is_active"]


class BreedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Breed
        fields = ["id", "species", "name", "local_names", "description", "is_active"]


class AnimalCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalCategory
        fields = ["id", "species", "code", "name", "description", "sort_order"]


class PhysiologicalStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhysiologicalStage
        fields = ["id", "species", "code", "name", "description", "sort_order"]


class ProductionObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionObjective
        fields = ["id", "code", "name", "description", "sort_order"]


# --- Lots ------------------------------------------------------------------------------


class AnimalGroupSerializer(ModelCleanMixin, serializers.ModelSerializer):
    farm = WritableFarmField()
    animals_count = serializers.IntegerField(read_only=True)
    species_name = serializers.CharField(source="species.name", read_only=True, default=None)

    class Meta:
        model = AnimalGroup
        fields = [
            "id",
            "farm",
            "name",
            "species",
            "species_name",
            "description",
            "is_active",
            "is_demo",
            "animals_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_demo", "created_at", "updated_at"]
        # Unicité vérifiée dans validate() avec un message rattaché au bon champ.
        validators = []

    def validate_species(self, value):
        if value and not value.is_active:
            raise serializers.ValidationError("Cette espèce n'est pas encore prise en charge.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        farm = attrs.get("farm") or getattr(self.instance, "farm", None)
        name = attrs.get("name", getattr(self.instance, "name", None))
        qs = AnimalGroup.objects.filter(farm=farm, name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if farm and name and qs.exists():
            raise serializers.ValidationError({"name": "Un lot porte déjà ce nom dans cette exploitation."})
        return attrs


# --- Animaux ---------------------------------------------------------------------------


class AnimalSerializer(ModelCleanMixin, serializers.ModelSerializer):
    farm = WritableFarmField()
    group = FarmScopedRelatedField(AnimalGroup, required=False, allow_null=True)
    species_name = serializers.CharField(source="species.name", read_only=True)
    breed_name = serializers.CharField(source="breed.name", read_only=True, default=None)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    physiological_stage_name = serializers.CharField(
        source="physiological_stage.name", read_only=True, default=None
    )
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)
    sex_label = serializers.CharField(source="get_sex_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    age_days = serializers.SerializerMethodField()
    estimated_age_months = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        write_only=True,
        required=False,
        allow_null=True,
        help_text=(
            "Âge estimé (mois) si la date de naissance est inconnue : "
            "la date est alors calculée et marquée estimée."
        ),
    )
    last_weight = serializers.SerializerMethodField()

    class Meta:
        model = Animal
        fields = [
            "id",
            "uuid",
            "farm",
            "tag_number",
            "name",
            "species",
            "species_name",
            "breed",
            "breed_name",
            "sex",
            "sex_label",
            "birth_date",
            "birth_date_is_estimated",
            "estimated_age_months",
            "age_days",
            "initial_weight_kg",
            "last_weight",
            "category",
            "category_name",
            "physiological_stage",
            "physiological_stage_name",
            "group",
            "group_name",
            "registered_on",
            "observations",
            "status",
            "status_label",
            "archived_at",
            "is_demo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "uuid", "status", "archived_at", "is_demo", "created_at", "updated_at"]
        # Unicité vérifiée dans validate() avec un message rattaché au bon champ.
        validators = []

    def get_age_days(self, obj) -> int | None:
        return obj.age_in_days()

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_last_weight(self, obj):
        weighing = obj.weighings.order_by("-weighed_on").first()
        if weighing is None:
            return None
        return {"weight_kg": str(weighing.weight_kg), "weighed_on": weighing.weighed_on, "unit": "kg"}

    def validate_species(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Cette espèce n'est pas encore prise en charge.")
        return value

    def validate(self, attrs):
        months = attrs.pop("estimated_age_months", None)
        if months is not None:
            if attrs.get("birth_date"):
                raise serializers.ValidationError(
                    {
                        "estimated_age_months": (
                            "Indiquez soit la date de naissance, soit l'âge estimé, pas les deux."
                        )
                    }
                )
            if months < 0:
                raise serializers.ValidationError({"estimated_age_months": "L'âge ne peut pas être négatif."})
            attrs["birth_date"] = timezone.localdate() - timezone.timedelta(days=round(float(months) * 30.44))
            attrs["birth_date_is_estimated"] = True
        attrs = super().validate(attrs)
        farm = attrs.get("farm") or getattr(self.instance, "farm", None)
        tag = attrs.get("tag_number", getattr(self.instance, "tag_number", None))
        qs = Animal.objects.filter(farm=farm, tag_number=tag)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if farm and tag and qs.exists():
            raise serializers.ValidationError(
                {"tag_number": "Ce numéro est déjà utilisé dans cette exploitation."}
            )
        return attrs


class AnimalArchiveSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[("SOLD", "Vendu"), ("DEAD", "Mort"), ("ARCHIVED", "Archivé")])
    note = serializers.CharField(required=False, allow_blank=True)


class AnimalObservationSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    author_email = serializers.EmailField(source="author.email", read_only=True, default=None)

    class Meta:
        model = AnimalObservation
        fields = ["id", "observed_on", "kind", "kind_label", "text", "author_email", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_observed_on(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("La date ne peut pas être dans le futur.")
        return value
