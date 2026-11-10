from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.serializers import ModelCleanMixin, WritableFarmField
from core.viewsets import ReadOnlyStatusSerializerMixin
from governance.models import SourceDocument

from .models import (
    InclusionConstraint,
    Ingredient,
    IngredientCategory,
    IngredientComposition,
    IngredientPrice,
    Nutrient,
    NutritionalReference,
    NutritionalRequirement,
    NutritionSystem,
)


class NutritionSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionSystem
        fields = ["id", "code", "name", "version", "description", "is_active"]


class NutrientSerializer(serializers.ModelSerializer):
    unit_label = serializers.CharField(read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    system_code = serializers.CharField(source="system.code", read_only=True, default=None)

    class Meta:
        model = Nutrient
        fields = [
            "id",
            "code",
            "name",
            "category",
            "category_label",
            "amount_unit",
            "basis",
            "unit_label",
            "system",
            "system_code",
            "description",
            "sort_order",
            "is_active",
        ]


class IngredientCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = IngredientCategory
        fields = ["id", "code", "name", "description", "sort_order"]


class SourceSummaryField(serializers.PrimaryKeyRelatedField):
    """Écriture : identifiant de la source. Lecture : résumé (titre, DEMO)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("queryset", SourceDocument.objects.all())
        super().__init__(**kwargs)

    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        return {"id": value.pk, "title": str(value), "is_demo": value.is_demo}


# --- Ingrédients -------------------------------------------------------------------------


class IngredientSerializer(ReadOnlyStatusSerializerMixin, serializers.ModelSerializer):
    farm = WritableFarmField(required=False, allow_null=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_code = serializers.CharField(source="category.code", read_only=True)
    scope = serializers.SerializerMethodField()
    source = SourceSummaryField(required=False, allow_null=True)
    # Teneur en matière sèche utilisable par le moteur (annotation de la vue ; absent hors liste).
    ready_for_engine = serializers.BooleanField(read_only=True, default=None)

    class Meta:
        model = Ingredient
        fields = [
            "id",
            "name",
            "local_names",
            "category",
            "category_name",
            "category_code",
            "description",
            "farm",
            "scope",
            "observations",
            "is_active",
            "source",
            "reference_date",
            "ready_for_engine",
            "is_demo",
            "status",
            "status_label",
            "validated_by_email",
            "validated_at",
            "validation_comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        # Unicité vérifiée dans validate() avec un message rattaché au bon champ.
        validators = []

    def get_scope(self, obj) -> str:
        return "private" if obj.farm_id else "catalog"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is not None and "farm" in attrs and attrs["farm"] != self.instance.farm:
            raise serializers.ValidationError({"farm": "Un ingrédient ne peut pas changer de catalogue."})
        farm = attrs.get("farm", getattr(self.instance, "farm", None))
        name = attrs.get("name", getattr(self.instance, "name", ""))
        qs = Ingredient.objects.filter(name__iexact=name, farm=farm)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({"name": "Un ingrédient porte déjà ce nom dans ce catalogue."})
        return attrs


class CompositionSerializer(ModelCleanMixin, ReadOnlyStatusSerializerMixin, serializers.ModelSerializer):
    source = SourceSummaryField(required=False, allow_null=True)
    nutrient_code = serializers.CharField(source="nutrient.code", read_only=True)
    nutrient_name = serializers.CharField(source="nutrient.name", read_only=True)
    unit_label = serializers.CharField(source="nutrient.unit_label", read_only=True)
    system_code = serializers.CharField(source="nutrient.system.code", read_only=True, default=None)
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)

    class Meta:
        model = IngredientComposition
        fields = [
            "id",
            "ingredient",
            "ingredient_name",
            "nutrient",
            "nutrient_code",
            "nutrient_name",
            "system_code",
            "value",
            "unit_label",
            "analysis_method",
            "sample_origin",
            "notes",
            "source",
            "reference_date",
            "is_demo",
            "status",
            "status_label",
            "validated_by_email",
            "validated_at",
            "validation_comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        # Unicité vérifiée dans validate() avec un message rattaché au bon champ.
        validators = []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is not None:
            for field in ("ingredient", "nutrient"):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError(
                        {field: "Ce champ ne peut pas être modifié ; créez une nouvelle valeur."}
                    )
        ingredient = attrs.get("ingredient", getattr(self.instance, "ingredient", None))
        nutrient = attrs.get("nutrient", getattr(self.instance, "nutrient", None))
        source = attrs.get("source", getattr(self.instance, "source", None))
        qs = IngredientComposition.objects.filter(ingredient=ingredient, nutrient=nutrient, source=source)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"source": "Une valeur existe déjà pour ce nutriment avec cette source : modifiez-la plutôt."}
            )
        if (
            ingredient
            and ingredient.is_demo
            and not attrs.get("is_demo", getattr(self.instance, "is_demo", False))
        ):
            raise serializers.ValidationError(
                {"is_demo": "La composition d'un ingrédient DEMO doit être marquée DEMO."}
            )
        return attrs


class IngredientDetailSerializer(IngredientSerializer):
    composition_table = serializers.SerializerMethodField()

    class Meta(IngredientSerializer.Meta):
        fields = [*IngredientSerializer.Meta.fields, "composition_table"]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_composition_table(self, obj):
        """Une ligne par nutriment actif : valeur validée, autres valeurs, ou « inconnue » (jamais zéro)."""
        compositions = {}
        for comp in obj.compositions.select_related("source", "validated_by", "nutrient__system"):
            compositions.setdefault(comp.nutrient_id, []).append(comp)
        rows = []
        for nutrient in (
            Nutrient.objects.filter(is_active=True).select_related("system").order_by("sort_order", "code")
        ):
            entries = compositions.get(nutrient.pk, [])
            validated = next((c for c in entries if c.status == "VALIDATED" and not c.is_demo), None)
            rows.append(
                {
                    "nutrient": NutrientSerializer(nutrient).data,
                    "known": bool(entries),
                    "validated_value": str(validated.value) if validated else None,
                    "values": CompositionSerializer(entries, many=True, context=self.context).data,
                }
            )
        return rows


# --- Prix --------------------------------------------------------------------------------


class IngredientPriceSerializer(ModelCleanMixin, serializers.ModelSerializer):
    farm = WritableFarmField()
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)

    class Meta:
        model = IngredientPrice
        fields = [
            "id",
            "farm",
            "ingredient",
            "ingredient_name",
            "price_per_kg_as_fed",
            "currency",
            "valid_from",
            "supplier",
            "location",
            "quantity_available_kg",
            "notes",
            "is_demo",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_demo", "created_at", "updated_at"]

    def validate_currency(self, value):
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Code devise ISO à 3 lettres attendu (ex. XOF).")
        return value

    def validate_price_per_kg_as_fed(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le prix doit être supérieur à zéro.")
        return value


# --- Références et besoins -------------------------------------------------------------


class RequirementSerializer(ModelCleanMixin, serializers.ModelSerializer):
    nutrient_code = serializers.CharField(source="nutrient.code", read_only=True)
    nutrient_name = serializers.CharField(source="nutrient.name", read_only=True)
    unit_label = serializers.CharField(read_only=True)
    expression_label = serializers.CharField(source="get_expression_display", read_only=True)

    class Meta:
        model = NutritionalRequirement
        fields = [
            "id",
            "reference",
            "nutrient",
            "nutrient_code",
            "nutrient_name",
            "expression",
            "expression_label",
            "min_value",
            "target_value",
            "max_value",
            "unit_label",
            "notes",
        ]
        read_only_fields = ["id"]
        # Unicité vérifiée dans validate() avec un message rattaché au bon champ.
        validators = []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        values = [
            attrs.get(k, getattr(self.instance, k, None)) for k in ("min_value", "target_value", "max_value")
        ]
        if all(v is None for v in values):
            raise serializers.ValidationError("Renseignez au moins une valeur (minimum, cible ou maximum).")
        low, target, high = values
        if any(v is not None and v < 0 for v in values):
            raise serializers.ValidationError("Les valeurs ne peuvent pas être négatives.")
        if low is not None and high is not None and low > high:
            raise serializers.ValidationError(
                {"max_value": "Le maximum doit être supérieur ou égal au minimum."}
            )
        if target is not None and (
            (low is not None and target < low) or (high is not None and target > high)
        ):
            raise serializers.ValidationError(
                {"target_value": "La cible doit être comprise entre le minimum et le maximum."}
            )
        reference = attrs.get("reference", getattr(self.instance, "reference", None))
        nutrient = attrs.get("nutrient", getattr(self.instance, "nutrient", None))
        expression = attrs.get("expression", getattr(self.instance, "expression", None))
        qs = NutritionalRequirement.objects.filter(
            reference=reference, nutrient=nutrient, expression=expression
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({"nutrient": "Ce besoin est déjà défini pour cette référence."})
        return attrs


class ReferenceSerializer(ModelCleanMixin, ReadOnlyStatusSerializerMixin, serializers.ModelSerializer):
    source = SourceSummaryField(required=False, allow_null=True)
    species_name = serializers.CharField(source="species.name", read_only=True)
    system_code = serializers.CharField(source="system.code", read_only=True)
    breed_name = serializers.CharField(source="breed.name", read_only=True, default=None)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    physiological_stage_name = serializers.CharField(
        source="physiological_stage.name", read_only=True, default=None
    )
    objective_name = serializers.CharField(source="objective.name", read_only=True, default=None)
    requirements = RequirementSerializer(many=True, read_only=True)

    class Meta:
        model = NutritionalReference
        fields = [
            "id",
            "name",
            "species",
            "species_name",
            "breed",
            "breed_name",
            "category",
            "category_name",
            "physiological_stage",
            "physiological_stage_name",
            "objective",
            "objective_name",
            "system",
            "system_code",
            "age_min_months",
            "age_max_months",
            "weight_min_kg",
            "weight_max_kg",
            "dm_intake_min_kg_day",
            "dm_intake_max_kg_day",
            "application_conditions",
            "notes",
            "source",
            "reference_date",
            "is_demo",
            "status",
            "status_label",
            "validated_by_email",
            "validated_at",
            "validation_comment",
            "requirements",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        for low, high, label in (
            ("age_min_months", "age_max_months", "âge"),
            ("weight_min_kg", "weight_max_kg", "poids"),
            ("dm_intake_min_kg_day", "dm_intake_max_kg_day", "ingestion"),
        ):
            a = attrs.get(low, getattr(self.instance, low, None))
            b = attrs.get(high, getattr(self.instance, high, None))
            if a is not None and b is not None and a > b:
                raise serializers.ValidationError(
                    {high: f"La borne maximale ({label}) doit être ≥ à la borne minimale."}
                )
        if (
            self.instance is not None
            and "system" in attrs
            and attrs["system"] != self.instance.system
            and self.instance.requirements.exists()
        ):
            raise serializers.ValidationError(
                {"system": "Impossible de changer de système : des besoins y sont déjà exprimés."}
            )
        return attrs


class InclusionConstraintSerializer(ReadOnlyStatusSerializerMixin, serializers.ModelSerializer):
    source = SourceSummaryField(required=False, allow_null=True)
    target_label = serializers.SerializerMethodField()

    class Meta:
        model = InclusionConstraint
        fields = [
            "id",
            "species",
            "animal_category",
            "ingredient",
            "ingredient_category",
            "target_label",
            "min_pct_dm",
            "max_pct_dm",
            "rationale",
            "source",
            "reference_date",
            "is_demo",
            "status",
            "status_label",
            "validated_by_email",
            "validated_at",
            "validation_comment",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_target_label(self, obj) -> str:
        return str(obj.ingredient or obj.ingredient_category)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        ingredient = attrs.get("ingredient", getattr(self.instance, "ingredient", None))
        category = attrs.get("ingredient_category", getattr(self.instance, "ingredient_category", None))
        if bool(ingredient) == bool(category):
            raise serializers.ValidationError(
                "Choisissez soit un ingrédient, soit une catégorie d'ingrédients."
            )
        if ingredient is not None and ingredient.farm_id is not None:
            raise serializers.ValidationError(
                {"ingredient": "Les contraintes portent sur le catalogue commun uniquement."}
            )
        low = attrs.get("min_pct_dm", getattr(self.instance, "min_pct_dm", None))
        high = attrs.get("max_pct_dm", getattr(self.instance, "max_pct_dm", None))
        if low is None and high is None:
            raise serializers.ValidationError("Renseignez au moins une borne.")
        for value in (low, high):
            if value is not None and not (0 <= value <= 100):
                raise serializers.ValidationError("Les bornes sont des pourcentages entre 0 et 100.")
        if low is not None and high is not None and low > high:
            raise serializers.ValidationError({"max_pct_dm": "Le maximum doit être ≥ au minimum."})
        return attrs


class CompositionImportSerializer(serializers.Serializer):
    file = serializers.FileField()
    source = serializers.PrimaryKeyRelatedField(queryset=SourceDocument.objects.all())
    is_demo = serializers.BooleanField(default=False)
