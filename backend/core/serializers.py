from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import CheckConstraint
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from farms.access import writable_farms

# Messages des contraintes CHECK de la base susceptibles d'être atteintes par une saisie.
CHECK_MESSAGES = {
    "template_weight_positive": "Le poids minimal doit être strictement positif.",
    "template_weight_ordered": "Le poids minimal doit être inférieur ou égal au poids maximal.",
    "template_intake_positive": "La matière sèche par animal et par jour doit être strictement positive.",
    "templateitem_pct_range": (
        "La part d'un aliment dans la matière sèche doit être comprise entre 0 et 100 %."
    ),
    "season_months_valid": "Les mois d'une saison vont de 1 (janvier) à 12 (décembre).",
    "sourcedocument_year_plausible": "L'année de la source n'est pas plausible.",
    "animal_initial_weight_positive": "Le poids initial doit être strictement positif.",
    "composition_value_non_negative": "Une teneur ne peut pas être négative.",
    "price_positive": "Le prix doit être strictement positif.",
    "price_quantity_non_negative": "La quantité disponible ne peut pas être négative.",
    "reference_age_range_ordered": "L'âge minimal doit être inférieur ou égal à l'âge maximal.",
    "reference_weight_range_ordered": "Le poids minimal doit être inférieur ou égal au poids maximal.",
    "reference_intake_range_ordered": "L'ingestion minimale doit être inférieure ou égale à la maximale.",
    "reference_values_positive": "Les âges, poids et quantités d'ingestion doivent être positifs.",
    "requirement_has_a_value": "Indiquez au moins une valeur (minimum, cible ou maximum).",
    "requirement_values_non_negative": "Les valeurs d'un besoin ne peuvent pas être négatives.",
    "requirement_min_le_max": "Le minimum doit être inférieur ou égal au maximum.",
    "requirement_min_le_target": "Le minimum doit être inférieur ou égal à la cible.",
    "requirement_target_le_max": "La cible doit être inférieure ou égale au maximum.",
    "inclusion_targets_ingredient_xor_category": "Choisissez un ingrédient ou une catégorie, pas les deux.",
    "inclusion_has_a_bound": "Indiquez au moins une borne (minimum ou maximum).",
    "inclusion_bounds_are_percentages": "Les bornes doivent être comprises entre 0 et 100 % de la MS.",
    "inclusion_min_le_max": "Le minimum doit être inférieur ou égal au maximum.",
    "formula_weight_positive": "Le poids de l'animal doit être strictement positif.",
    "ration_targets_animal_xor_group": "Une ration concerne un animal ou un lot, pas les deux.",
    "ration_dates_ordered": "La date de fin doit être postérieure à la date de début.",
    "ration_planned_quantity_positive": "La quantité prévue doit être strictement positive.",
    "feeding_targets_animal_xor_group": "Une distribution concerne un animal ou un lot, pas les deux.",
    "feeding_quantities_non_negative": "Les quantités ne peuvent pas être négatives.",
    "feeding_consumed_le_distributed": "La quantité consommée ne peut pas dépasser la quantité distribuée.",
    "feeding_refused_le_distributed": "La quantité refusée ne peut pas dépasser la quantité distribuée.",
    "weighing_weight_positive": "Le poids doit être strictement positif.",
    "growthrange_has_a_bound": "Indiquez au moins une borne de GMD.",
    "growthrange_min_le_max": "Le GMD minimal doit être inférieur ou égal au GMD maximal.",
    "growthrange_age_ordered": "L'âge minimal doit être inférieur ou égal à l'âge maximal.",
}


class ModelCleanMixin:
    """Applique la méthode `clean()` du modèle (règles de cohérence métier) lors de la validation DRF."""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        model = self.Meta.model
        instance = self.instance if self.instance is not None else model()
        for field, value in attrs.items():
            if not isinstance(getattr(model, field, None), property):
                try:
                    setattr(instance, field, value)
                except (TypeError, ValueError):
                    pass  # relations multiples ou champs calculés : ignorés ici
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "error_dict") else {"non_field_errors": exc.messages}
            ) from exc
        self._check_database_constraints(model, instance)
        return attrs

    @staticmethod
    def _check_database_constraints(model, instance):
        """Évalue les contraintes CHECK de la base avant l'enregistrement.

        Sans cela, une valeur interdite uniquement par PostgreSQL (ex. teneur négative) remonterait en
        erreur 500. Les valeurs NULL sont acceptées, comme le fait PostgreSQL.
        """
        errors = []
        for constraint in model._meta.constraints:
            if not isinstance(constraint, CheckConstraint):
                continue
            try:
                constraint.validate(model, instance)
            except DjangoValidationError:
                errors.append(
                    CHECK_MESSAGES.get(
                        constraint.name, f"Valeur non autorisée (règle « {constraint.name} »)."
                    )
                )
        if errors:
            raise serializers.ValidationError({"non_field_errors": errors})


@extend_schema_field(OpenApiTypes.INT)
class WritableFarmField(serializers.PrimaryKeyRelatedField):
    """Exploitation choisie à la création : uniquement parmi celles où l'utilisateur peut écrire."""

    default_error_messages = {
        "does_not_exist": "Exploitation introuvable ou non modifiable avec votre compte.",
    }

    def get_queryset(self):
        return writable_farms(self.context["request"].user)


@extend_schema_field(OpenApiTypes.INT)
class FarmScopedRelatedField(serializers.PrimaryKeyRelatedField):
    """Relation vers un objet d'exploitation (lot, animal, formule…) : limitée aux exploitations lisibles.

    La cohérence fine (même exploitation que l'objet édité) est vérifiée par `clean()`.
    """

    def __init__(self, model, **kwargs):
        self.model = model
        super().__init__(**kwargs)

    def get_queryset(self):
        from farms.access import readable_farms

        return self.model.objects.filter(farm__in=readable_farms(self.context["request"].user))


class ValidationActionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")
