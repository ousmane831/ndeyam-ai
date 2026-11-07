from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from animals.models import (
    Animal,
    AnimalCategory,
    AnimalGroup,
    Breed,
    PhysiologicalStage,
    ProductionObjective,
    Species,
)
from core.serializers import FarmScopedRelatedField, ModelCleanMixin, WritableFarmField
from nutrition.models import Ingredient, NutritionalReference

from .analysis import analyse_ration
from .models import FeedFormula, FeedFormulaIngredient, FormulaMode, FormulaStatus


class FormulaItemSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)

    class Meta:
        model = FeedFormulaIngredient
        fields = [
            "id",
            "ingredient",
            "ingredient_name",
            "inclusion_pct_dm",
            "inclusion_pct_as_fed",
            "quantity_dm_kg",
            "quantity_as_fed_kg",
            "price_per_kg_as_fed",
            "cost_per_day",
        ]
        read_only_fields = fields


class ManualItemInputSerializer(serializers.Serializer):
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.filter(is_active=True))
    quantity_as_fed_kg = serializers.DecimalField(max_digits=9, decimal_places=4, min_value=Decimal("0.0001"))


class FeedFormulaSerializer(ModelCleanMixin, serializers.ModelSerializer):
    farm = WritableFarmField()
    animal = FarmScopedRelatedField(Animal, required=False, allow_null=True)
    group = FarmScopedRelatedField(AnimalGroup, required=False, allow_null=True)
    items = FormulaItemSerializer(many=True, read_only=True)
    manual_items = ManualItemInputSerializer(many=True, write_only=True, required=False)
    mode_label = serializers.CharField(source="get_mode_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    validated_by_email = serializers.EmailField(source="validated_by.email", read_only=True, default=None)

    class Meta:
        model = FeedFormula
        fields = [
            "id",
            "farm",
            "name",
            "species",
            "reference",
            "mode",
            "mode_label",
            "status",
            "status_label",
            "is_demo",
            "animal",
            "group",
            "animal_weight_kg",
            "animal_age_months",
            "physiological_stage",
            "objective",
            "dm_intake_kg_day",
            "as_fed_kg_day",
            "cost_per_day",
            "cost_per_kg_as_fed",
            "currency",
            "items",
            "manual_items",
            "result_snapshot",
            "warnings",
            "solver_status",
            "engine_version",
            "validated_by_email",
            "validated_at",
            "review_comment",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "mode",
            "status",
            "is_demo",
            "reference",
            "dm_intake_kg_day",
            "as_fed_kg_day",
            "cost_per_day",
            "cost_per_kg_as_fed",
            "currency",
            "result_snapshot",
            "warnings",
            "solver_status",
            "engine_version",
            "validated_at",
            "review_comment",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        farm = attrs.get("farm") or getattr(self.instance, "farm", None)
        for field in ("animal", "group"):
            target = attrs.get(field)
            if target is not None and farm is not None and target.farm_id != farm.pk:
                raise serializers.ValidationError(
                    {field: "Doit appartenir à la même exploitation que la formule."}
                )
        species = attrs.get("species") or getattr(self.instance, "species", None)
        if species is not None and not species.is_active:
            raise serializers.ValidationError({"species": "Cette espèce n'est pas encore prise en charge."})
        items = attrs.get("manual_items")
        if self.instance is None and not items:
            raise serializers.ValidationError(
                {"manual_items": "Ajoutez au moins un ingrédient avec sa quantité."}
            )
        if items is not None:
            ids = [i["ingredient"].pk for i in items]
            if len(ids) != len(set(ids)):
                raise serializers.ValidationError(
                    {"manual_items": "Chaque ingrédient ne doit apparaître qu'une fois."}
                )
            for item in items:
                ing = item["ingredient"]
                if ing.farm_id is not None and farm is not None and ing.farm_id != farm.pk:
                    raise serializers.ValidationError(
                        {"manual_items": f"« {ing.name} » est un ingrédient d'une autre exploitation."}
                    )
        if self.instance is not None and self.instance.mode != FormulaMode.MANUAL and items is not None:
            raise serializers.ValidationError(
                {"manual_items": "Seules les formules manuelles sont modifiables ainsi."}
            )
        return super().validate(attrs)  # règles du modèle et contraintes CHECK (ModelCleanMixin)

    @transaction.atomic
    def _apply_items(self, formula, items):
        analysis = analyse_ration(formula.farm, [(i["ingredient"], i["quantity_as_fed_kg"]) for i in items])
        formula.items.all().delete()
        for line in analysis["lines"]:
            FeedFormulaIngredient.objects.create(
                formula=formula,
                ingredient=line["ingredient"],
                quantity_as_fed_kg=line["quantity_as_fed_kg"],
                quantity_dm_kg=line["quantity_dm_kg"],
                inclusion_pct_as_fed=line["inclusion_pct_as_fed"],
                inclusion_pct_dm=line["inclusion_pct_dm"],
                price=line["price"],
                price_per_kg_as_fed=line["price"].price_per_kg_as_fed if line["price"] else None,
                cost_per_day=line["cost"],
            )
        formula.as_fed_kg_day = analysis["total_as_fed_kg"]
        formula.dm_intake_kg_day = analysis["total_dm_kg"]
        formula.cost_per_day = analysis["cost_per_day"]
        formula.cost_per_kg_as_fed = analysis["cost_per_kg_as_fed"]
        formula.currency = analysis["currency"]
        formula.warnings = analysis["warnings"]
        formula.result_snapshot = {
            "kind": "manual_analysis",
            "nutrients": analysis["nutrients"],
            "sources": analysis["sources"],
            "disclaimer": analysis["disclaimer"],
        }
        # Toute modification d'une formule la remet en brouillon : elle doit être revérifiée.
        formula.status = FormulaStatus.DRAFT
        formula.validated_by = None
        formula.validated_at = None
        formula.save()
        return formula

    def create(self, validated_data):
        items = validated_data.pop("manual_items")
        validated_data["is_demo"] = validated_data["farm"].is_demo  # toujours celui de l'exploitation
        formula = FeedFormula.objects.create(mode=FormulaMode.MANUAL, **validated_data)
        return self._apply_items(formula, items)

    def update(self, instance, validated_data):
        items = validated_data.pop("manual_items", None)
        validated_data.pop("farm", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if items is not None:
            self._apply_items(instance, items)
        return instance


class FormulaReviewSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class CalculationEntrySerializer(serializers.Serializer):
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.filter(is_active=True))
    price_per_kg_as_fed = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=Decimal("0.01")
    )
    available_kg_as_fed = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=Decimal("0")
    )


class CalculationRequestSerializer(serializers.Serializer):
    """Demande de calcul au moteur d'optimisation."""

    farm = WritableFarmField()
    name = serializers.CharField(max_length=200)
    mode = serializers.ChoiceField(
        choices=[(FormulaMode.ECONOMIC, "Économique"), (FormulaMode.BALANCED, "Équilibré")]
    )
    species = serializers.PrimaryKeyRelatedField(
        queryset=Species.objects.filter(is_active=True), required=False
    )
    animal = FarmScopedRelatedField(Animal, required=False, allow_null=True)
    group = FarmScopedRelatedField(AnimalGroup, required=False, allow_null=True)
    reference = serializers.PrimaryKeyRelatedField(
        queryset=NutritionalReference.objects.all(), required=False, allow_null=True
    )
    breed = serializers.PrimaryKeyRelatedField(queryset=Breed.objects.all(), required=False, allow_null=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=AnimalCategory.objects.all(), required=False, allow_null=True
    )
    physiological_stage = serializers.PrimaryKeyRelatedField(
        queryset=PhysiologicalStage.objects.all(), required=False, allow_null=True
    )
    objective = serializers.PrimaryKeyRelatedField(
        queryset=ProductionObjective.objects.all(), required=False, allow_null=True
    )
    animal_weight_kg = serializers.DecimalField(
        max_digits=7, decimal_places=2, required=False, allow_null=True, min_value=Decimal("0.01")
    )
    animal_age_months = serializers.DecimalField(
        max_digits=5, decimal_places=1, required=False, allow_null=True, min_value=Decimal("0")
    )
    ingredients = CalculationEntrySerializer(many=True)
    number_of_animals = serializers.IntegerField(required=False, min_value=1)
    duration_days = serializers.IntegerField(required=False, min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    save = serializers.BooleanField(default=True)

    def validate(self, attrs):
        farm = attrs["farm"]
        animal, group = attrs.get("animal"), attrs.get("group")
        for target in (animal, group):
            if target is not None and target.farm_id != farm.pk:
                raise serializers.ValidationError(
                    "L'animal ou le lot doit appartenir à l'exploitation choisie."
                )
        if animal is not None:
            # Profil pré-rempli depuis la fiche de l'animal (les valeurs saisies restent prioritaires).
            attrs.setdefault("species", animal.species)
            for field in ("breed", "category", "physiological_stage"):
                if attrs.get(field) is None:
                    attrs[field] = getattr(animal, field)
            if attrs.get("animal_weight_kg") is None:
                last = animal.weighings.order_by("-weighed_on").first()
                attrs["animal_weight_kg"] = last.weight_kg if last else animal.initial_weight_kg
            if attrs.get("animal_age_months") is None and animal.birth_date:
                months = Decimal(animal.age_in_days()) / Decimal("30.44")
                attrs["animal_age_months"] = months.quantize(Decimal("0.1"))
        if attrs.get("species") is None:
            raise serializers.ValidationError({"species": "Indiquez l'espèce ou choisissez un animal."})

        reference = attrs.get("reference")
        if reference is not None:
            if reference.species_id != attrs["species"].pk:
                raise serializers.ValidationError({"reference": "La référence concerne une autre espèce."})
            if farm.is_demo:
                usable = reference.is_demo and reference.status != "REJECTED"
                message = "Une exploitation DEMO n'utilise que des références DEMO."
            else:
                usable = reference.is_usable_for_engine
                message = (
                    "Cette référence n'est pas utilisable : seules les références validées (non DEMO) "
                    "le sont pour une exploitation réelle."
                )
            if not usable:
                raise serializers.ValidationError({"reference": message})

        entries = attrs["ingredients"]
        if not entries:
            raise serializers.ValidationError({"ingredients": "Proposez au moins un ingrédient."})
        ids = [e["ingredient"].pk for e in entries]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                {"ingredients": "Chaque ingrédient ne doit apparaître qu'une fois."}
            )
        visible = set(
            Ingredient.objects.filter(pk__in=ids)
            .filter(Q(farm__isnull=True) | Q(farm=farm))
            .values_list("pk", flat=True)
        )
        if set(ids) - visible:
            raise serializers.ValidationError(
                {"ingredients": "Un ingrédient appartient à une autre exploitation."}
            )
        if any(e.get("available_kg_as_fed") is not None for e in entries) and not (
            attrs.get("number_of_animals") and attrs.get("duration_days")
        ):
            raise serializers.ValidationError(
                {
                    "number_of_animals": (
                        "Pour tenir compte des quantités disponibles, "
                        "indiquez le nombre d'animaux et la durée (jours)."
                    )
                }
            )
        return attrs
