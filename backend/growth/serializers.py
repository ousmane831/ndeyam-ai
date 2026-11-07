from rest_framework import serializers

from animals.models import Animal, AnimalStatus
from core.serializers import FarmScopedRelatedField, ModelCleanMixin
from core.viewsets import ReadOnlyStatusSerializerMixin
from nutrition.serializers import SourceSummaryField

from .models import GrowthMonitoringRange, Weighing, WeighingMethod


class WeighingSerializer(ModelCleanMixin, serializers.ModelSerializer):
    animal = FarmScopedRelatedField(Animal)
    animal_tag = serializers.CharField(source="animal.tag_number", read_only=True)
    unit = serializers.SerializerMethodField()
    method_label = serializers.CharField(source="get_method_display", read_only=True)
    recorded_by_email = serializers.EmailField(source="recorded_by.email", read_only=True, default=None)

    class Meta:
        model = Weighing
        fields = [
            "id",
            "animal",
            "animal_tag",
            "weighed_on",
            "weight_kg",
            "unit",
            "method",
            "method_label",
            "observations",
            "is_demo",
            "recorded_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_demo", "created_at", "updated_at"]
        # Unicité vérifiée dans validate() avec un message explicite.
        validators = []

    def get_unit(self, obj) -> str:
        return Weighing.UNIT

    def validate_weight_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le poids doit être supérieur à zéro.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is not None and "animal" in attrs and attrs["animal"] != self.instance.animal:
            raise serializers.ValidationError(
                {"animal": "Une pesée ne peut pas être déplacée vers un autre animal."}
            )
        animal = attrs.get("animal", getattr(self.instance, "animal", None))
        day = attrs.get("weighed_on", getattr(self.instance, "weighed_on", None))
        if animal is not None and animal.status != AnimalStatus.ACTIVE and self.instance is None:
            raise serializers.ValidationError(
                {"animal": "Cet animal n'est plus présent dans l'exploitation."}
            )
        qs = Weighing.objects.filter(animal=animal, weighed_on=day)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if animal is not None and day and qs.exists():
            raise serializers.ValidationError(
                {"weighed_on": "Une pesée existe déjà pour cet animal à cette date."}
            )
        return attrs


class BulkWeighingEntrySerializer(serializers.Serializer):
    animal = serializers.IntegerField()
    weight_kg = serializers.DecimalField(max_digits=7, decimal_places=2)
    observations = serializers.CharField(required=False, allow_blank=True, default="")


class BulkWeighingSerializer(serializers.Serializer):
    weighed_on = serializers.DateField()
    method = serializers.ChoiceField(choices=WeighingMethod.choices, default=WeighingMethod.SCALE)
    entries = BulkWeighingEntrySerializer(many=True)

    def validate_entries(self, value):
        if not value:
            raise serializers.ValidationError("Ajoutez au moins une pesée.")
        if len(value) > 500:
            raise serializers.ValidationError("500 pesées maximum par séance.")
        ids = [e["animal"] for e in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Un animal apparaît plusieurs fois dans la séance.")
        return value


class GrowthRangeSerializer(ReadOnlyStatusSerializerMixin, serializers.ModelSerializer):
    source = SourceSummaryField(required=False, allow_null=True)

    class Meta:
        model = GrowthMonitoringRange
        fields = [
            "id",
            "name",
            "species",
            "breed",
            "category",
            "physiological_stage",
            "sex",
            "age_min_days",
            "age_max_days",
            "adg_min_g",
            "adg_max_g",
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
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        def value(field):
            return attrs.get(field, getattr(self.instance, field, None))

        if value("adg_min_g") is None and value("adg_max_g") is None:
            raise serializers.ValidationError("Renseignez au moins une borne de GMD.")
        for low, high in (("adg_min_g", "adg_max_g"), ("age_min_days", "age_max_days")):
            if value(low) is not None and value(high) is not None and value(low) > value(high):
                raise serializers.ValidationError(
                    {high: "La borne maximale doit être ≥ à la borne minimale."}
                )
        species = value("species")
        for field in ("breed", "category", "physiological_stage"):
            related = value(field)
            if related is not None and species is not None and related.species_id != species.pk:
                raise serializers.ValidationError({field: "Ne correspond pas à l'espèce de la plage."})
        return attrs
