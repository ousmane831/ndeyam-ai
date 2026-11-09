from decimal import Decimal

from rest_framework import serializers

from animals.models import Animal, AnimalGroup
from core.serializers import FarmScopedRelatedField, WritableFarmField
from formulations.models import FeedFormula, FormulaMode, FormulaStatus

from .models import FeedingRecord, Ration


def _check_same_farm(attrs, instance, fields):
    farm = attrs.get("farm") or getattr(instance, "farm", None)
    for field in fields:
        target = attrs.get(field)
        if target is not None and farm is not None and target.farm_id != farm.pk:
            raise serializers.ValidationError({field: "Doit appartenir à la même exploitation."})


def ration_blocker(formula):
    """Raison pour laquelle cette formule ne peut pas devenir une ration (None si elle le peut).

    - Formule calculée par le moteur : seulement une fois validée par un expert. Une estimation
      mathématique ne nourrit jamais un animal réel sans vérification humaine.
    - Formule saisie à la main : c'est la ration que l'éleveur distribue déjà ; autorisée sauf rejet.
    - Exploitation DEMO : données fictives jamais validables, la démonstration reste possible.
    """
    if formula.farm.is_demo:
        return None
    if formula.mode == FormulaMode.MANUAL:
        if formula.status == FormulaStatus.REJECTED:
            return "Cette formule a été rejetée par un expert : elle ne peut pas devenir une ration."
        return None
    if formula.status != FormulaStatus.VALIDATED:
        return (
            "Seule une formule validée par un expert peut devenir une ration. "
            "Demandez d'abord la vérification de cette estimation."
        )
    return None


def _check_one_target(attrs, instance):
    animal = attrs.get("animal", getattr(instance, "animal", None))
    group = attrs.get("group", getattr(instance, "group", None))
    if bool(animal) == bool(group):
        raise serializers.ValidationError(
            "Associez soit un animal, soit un lot (l'un des deux, pas les deux)."
        )


class RationSerializer(serializers.ModelSerializer):
    farm = WritableFarmField()
    formula = FarmScopedRelatedField(FeedFormula)
    animal = FarmScopedRelatedField(Animal, required=False, allow_null=True)
    group = FarmScopedRelatedField(AnimalGroup, required=False, allow_null=True)
    formula_name = serializers.CharField(source="formula.name", read_only=True)
    formula_status = serializers.CharField(source="formula.status", read_only=True)
    formula_status_label = serializers.CharField(source="formula.get_status_display", read_only=True)
    target_label = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Ration
        fields = [
            "id",
            "farm",
            "name",
            "formula",
            "formula_name",
            "formula_status",
            "formula_status_label",
            "animal",
            "group",
            "target_label",
            "start_date",
            "end_date",
            "planned_as_fed_kg_per_animal_day",
            "status",
            "status_label",
            "is_demo",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "is_demo", "created_at", "updated_at"]

    def get_target_label(self, obj) -> str:
        return f"Animal {obj.animal}" if obj.animal_id else f"Lot {obj.group}"

    def validate(self, attrs):
        _check_same_farm(attrs, self.instance, ("formula", "animal", "group"))
        _check_one_target(attrs, self.instance)
        formula = attrs.get("formula")
        if formula is not None:
            problem = ration_blocker(formula)
            if problem:
                raise serializers.ValidationError({"formula": problem})
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "La date de fin doit suivre la date de début."})
        planned = attrs.get("planned_as_fed_kg_per_animal_day")
        if planned is not None and planned <= 0:
            raise serializers.ValidationError(
                {"planned_as_fed_kg_per_animal_day": "La quantité doit être positive."}
            )
        return attrs


class EndRationSerializer(serializers.Serializer):
    end_date = serializers.DateField()


class FeedingRecordSerializer(serializers.ModelSerializer):
    farm = WritableFarmField()
    ration = FarmScopedRelatedField(Ration, required=False, allow_null=True)
    animal = FarmScopedRelatedField(Animal, required=False, allow_null=True)
    group = FarmScopedRelatedField(AnimalGroup, required=False, allow_null=True)
    ration_name = serializers.CharField(source="ration.name", read_only=True, default=None)
    target_label = serializers.SerializerMethodField()
    recorded_by_email = serializers.EmailField(source="recorded_by.email", read_only=True, default=None)

    class Meta:
        model = FeedingRecord
        fields = [
            "id",
            "farm",
            "ration",
            "ration_name",
            "animal",
            "group",
            "target_label",
            "fed_on",
            "number_of_animals",
            "quantity_calculated_kg",
            "quantity_distributed_kg",
            "quantity_consumed_kg",
            "quantity_refused_kg",
            "estimated_cost",
            "currency",
            "notes",
            "is_demo",
            "recorded_by_email",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "quantity_calculated_kg",
            "estimated_cost",
            "currency",
            "is_demo",
            "created_at",
        ]

    def get_target_label(self, obj) -> str:
        return f"Animal {obj.animal}" if obj.animal_id else f"Lot {obj.group}"

    def validate(self, attrs):
        ration = attrs.get("ration", getattr(self.instance, "ration", None))
        if ration is not None and "animal" not in attrs and "group" not in attrs and self.instance is None:
            attrs["animal"], attrs["group"] = ration.animal, ration.group
        _check_same_farm(attrs, self.instance, ("ration", "animal", "group"))
        _check_one_target(attrs, self.instance)
        if ration is not None:
            animal = attrs.get("animal", getattr(self.instance, "animal", None))
            group = attrs.get("group", getattr(self.instance, "group", None))
            if (ration.animal_id, ration.group_id) != (
                getattr(animal, "pk", None),
                getattr(group, "pk", None),
            ):
                raise serializers.ValidationError("L'animal ou le lot doit être celui de la ration.")
        distributed = attrs.get(
            "quantity_distributed_kg", getattr(self.instance, "quantity_distributed_kg", None)
        )
        for field in ("quantity_consumed_kg", "quantity_refused_kg"):
            value = attrs.get(field, getattr(self.instance, field, None))
            if value is not None and distributed is not None and value > distributed:
                raise serializers.ValidationError({field: "Ne peut pas dépasser la quantité distribuée."})
        for field in ("quantity_distributed_kg", "quantity_consumed_kg", "quantity_refused_kg"):
            value = attrs.get(field)
            if value is not None and value < 0:
                raise serializers.ValidationError({field: "La quantité ne peut pas être négative."})
        if attrs.get("group") is not None and not attrs.get("number_of_animals"):
            raise serializers.ValidationError(
                {"number_of_animals": "Indiquez le nombre d'animaux nourris dans le lot."}
            )
        return attrs

    @staticmethod
    def compute_derived(record):
        """Quantité calculée (prévue par la ration) et coût estimé (prix moyen de la formule × distribué)."""
        ration = record.ration
        if ration and ration.planned_as_fed_kg_per_animal_day:
            heads = record.number_of_animals or 1
            record.quantity_calculated_kg = ration.planned_as_fed_kg_per_animal_day * Decimal(heads)
        else:
            record.quantity_calculated_kg = None
        formula = ration.formula if ration else None
        if formula and formula.cost_per_kg_as_fed is not None:
            record.estimated_cost = (formula.cost_per_kg_as_fed * record.quantity_distributed_kg).quantize(
                Decimal("0.01")
            )
            record.currency = formula.currency
        else:
            record.estimated_cost = None

    def create(self, validated_data):
        record = FeedingRecord(**validated_data)
        self.compute_derived(record)
        record.save()
        return record

    def update(self, instance, validated_data):
        validated_data.pop("farm", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        self.compute_derived(instance)
        instance.save()
        return instance
