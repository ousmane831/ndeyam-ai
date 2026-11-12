"""
Référentiel nutritionnel : systèmes, nutriments, ingrédients, compositions, prix, besoins.

Principe anti-mélange
---------------------
Chaque valeur (composition d'un ingrédient ou besoin d'un animal) est rattachée à un `Nutrient`
précis, qui fixe à la fois l'unité, la base d'expression (par kg de MS ou par kg brut) et le
système nutritionnel (INRA, NRC… ou « universel » pour MS, MAT, Ca, P…).
Le moteur ne compare que des valeurs portant sur le même `Nutrient` : il est donc impossible,
par construction, d'additionner des UFL (INRA) avec des Mcal d'EM (NRC).

Matière sèche
-------------
Toutes les compositions sont exprimées par kg de matière sèche (MS), à l'exception de la teneur
en MS elle-même, exprimée en g/kg de produit brut. Les conversions brut ↔ MS sont centralisées
dans `nutrition.units`.

Une composition absente signifie « inconnue » : elle n'est jamais remplacée par zéro.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from core.models import TimeStampedModel
from governance.models import ValidatedReferenceModel, ValidationStatus, validated_reference_constraints


class NutritionSystem(TimeStampedModel):
    code = models.CharField("code", max_length=32, unique=True)
    name = models.CharField("nom", max_length=150)
    version = models.CharField("version / édition", max_length=50, blank=True)
    description = models.TextField("description", blank=True)
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "système nutritionnel"
        verbose_name_plural = "systèmes nutritionnels"
        ordering = ["code"]

    def __str__(self):
        return f"{self.name} {self.version}".strip()


class NutrientCategory(models.TextChoices):
    DRY_MATTER = "DRY_MATTER", "Matière sèche"
    ENERGY = "ENERGY", "Énergie"
    PROTEIN = "PROTEIN", "Protéines / azote"
    FIBER = "FIBER", "Fibres"
    FAT = "FAT", "Matières grasses"
    MINERAL = "MINERAL", "Minéraux"
    OTHER = "OTHER", "Autre"


class AmountUnit(models.TextChoices):
    G = "g", "g"
    MG = "mg", "mg"
    UFL = "UFL", "UFL"
    UFV = "UFV", "UFV"
    MCAL = "Mcal", "Mcal"
    MJ = "MJ", "MJ"


class ExpressionBasis(models.TextChoices):
    DRY_MATTER = "DM", "par kg de matière sèche"
    AS_FED = "AS_FED", "par kg de produit brut"


class Nutrient(TimeStampedModel):
    code = models.CharField("code", max_length=32)
    name = models.CharField("nom", max_length=150)
    category = models.CharField("catégorie", max_length=16, choices=NutrientCategory.choices)
    amount_unit = models.CharField("unité de quantité", max_length=8, choices=AmountUnit.choices)
    basis = models.CharField(
        "base d'expression", max_length=8, choices=ExpressionBasis.choices, default=ExpressionBasis.DRY_MATTER
    )
    system = models.ForeignKey(
        NutritionSystem,
        verbose_name="système nutritionnel",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="nutrients",
        help_text="Vide = nutriment universel (MS, MAT, Ca, P…), utilisable quel que soit le système.",
    )
    description = models.TextField("description", blank=True)
    sort_order = models.PositiveSmallIntegerField("ordre", default=0)
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "nutriment"
        verbose_name_plural = "nutriments"
        ordering = ["sort_order", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["code"], condition=Q(system__isnull=True), name="nutrient_unique_universal_code"
            ),
            models.UniqueConstraint(fields=["system", "code"], name="nutrient_unique_code_per_system"),
            # Seule la matière sèche est exprimée sur le brut ; tout le reste l'est sur la MS.
            models.CheckConstraint(
                condition=Q(category="DRY_MATTER", basis="AS_FED", amount_unit="g")
                | ~Q(category="DRY_MATTER"),
                name="nutrient_dry_matter_in_g_per_kg_as_fed",
            ),
            models.CheckConstraint(
                condition=Q(basis="DM") | Q(category="DRY_MATTER"),
                name="nutrient_only_dry_matter_on_as_fed_basis",
            ),
        ]

    def __str__(self):
        return f"{self.code} ({self.unit_label})"

    @property
    def unit_label(self) -> str:
        suffix = "kg MS" if self.basis == ExpressionBasis.DRY_MATTER else "kg brut"
        return f"{self.amount_unit}/{suffix}"


class IngredientCategory(TimeStampedModel):
    code = models.CharField("code", max_length=32, unique=True)
    name = models.CharField("nom", max_length=120)
    description = models.TextField("description", blank=True)
    sort_order = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "catégorie d'ingrédient"
        verbose_name_plural = "catégories d'ingrédients"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Ingredient(ValidatedReferenceModel):
    name = models.CharField("nom", max_length=150)
    local_names = models.CharField("noms locaux", max_length=255, blank=True)
    category = models.ForeignKey(IngredientCategory, on_delete=models.PROTECT, related_name="ingredients")
    description = models.TextField("description", blank=True)
    farm = models.ForeignKey(
        "farms.Farm",
        verbose_name="exploitation propriétaire",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="private_ingredients",
        help_text="Vide = ingrédient du catalogue commun. Renseigné = ingrédient privé de l'exploitation.",
    )
    observations = models.TextField("observations", blank=True)
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "ingrédient"
        verbose_name_plural = "ingrédients"
        ordering = ["name"]
        constraints = [
            *validated_reference_constraints(),
            models.UniqueConstraint(
                Lower("name"), condition=Q(farm__isnull=True), name="ingredient_unique_name_in_catalog"
            ),
            models.UniqueConstraint(Lower("name"), "farm", name="ingredient_unique_name_per_farm"),
        ]

    def __str__(self):
        return self.name


class IngredientComposition(ValidatedReferenceModel):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="compositions")
    nutrient = models.ForeignKey(Nutrient, on_delete=models.PROTECT, related_name="compositions")
    value = models.DecimalField("valeur", max_digits=12, decimal_places=4)
    analysis_method = models.CharField("méthode d'analyse", max_length=255, blank=True)
    sample_origin = models.CharField("origine de l'échantillon", max_length=255, blank=True)
    notes = models.TextField("notes", blank=True)

    class Meta:
        verbose_name = "composition nutritionnelle"
        verbose_name_plural = "compositions nutritionnelles"
        ordering = ["ingredient__name", "nutrient__sort_order"]
        constraints = [
            *validated_reference_constraints(),
            models.CheckConstraint(condition=Q(value__gte=0), name="composition_value_non_negative"),
            models.UniqueConstraint(
                fields=["ingredient", "nutrient", "source"],
                nulls_distinct=False,
                name="composition_unique_per_source",
            ),
            # Une seule valeur validée par couple ingrédient/nutriment :
            # le moteur sait toujours laquelle utiliser.
            models.UniqueConstraint(
                fields=["ingredient", "nutrient"],
                condition=Q(status="VALIDATED"),
                name="composition_single_validated_value",
            ),
        ]

    def __str__(self):
        return f"{self.ingredient} — {self.nutrient.code} = {self.value} {self.nutrient.unit_label}"

    def clean(self):
        if self.value is not None and self.value < 0:
            # Également garanti par la contrainte CHECK : refusé ici pour renvoyer une erreur 400 lisible.
            raise ValidationError({"value": "Une teneur ne peut pas être négative."})
        if (
            self.nutrient_id
            and self.nutrient.category == NutrientCategory.DRY_MATTER
            and self.value is not None
        ):
            if not (0 < self.value <= 1000):
                raise ValidationError(
                    {"value": "La teneur en matière sèche doit être comprise entre 0 et 1000 g/kg brut."}
                )


class IngredientPrice(TimeStampedModel):
    farm = models.ForeignKey("farms.Farm", on_delete=models.CASCADE, related_name="ingredient_prices")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, related_name="prices")
    price_per_kg_as_fed = models.DecimalField("prix par kg brut", max_digits=12, decimal_places=2)
    currency = models.CharField("devise", max_length=3, default="XOF")
    valid_from = models.DateField("date du prix", default=timezone.localdate)
    supplier = models.CharField("fournisseur", max_length=200, blank=True)
    location = models.CharField("lieu d'achat", max_length=200, blank=True)
    quantity_available_kg = models.DecimalField(
        "quantité disponible (kg brut)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField("notes", blank=True)
    # Prix habituel pendant une saison (planification) ; vide = prix relevé à la date indiquée.
    season = models.ForeignKey(
        "seasons.Season", on_delete=models.PROTECT, null=True, blank=True, related_name="prices"
    )
    is_demo = models.BooleanField("donnée DEMO", default=False, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "prix d'ingrédient"
        verbose_name_plural = "prix des ingrédients"
        ordering = ["-valid_from"]
        constraints = [
            models.CheckConstraint(condition=Q(price_per_kg_as_fed__gt=0), name="price_positive"),
            models.CheckConstraint(
                condition=Q(quantity_available_kg__isnull=True) | Q(quantity_available_kg__gte=0),
                name="price_quantity_non_negative",
            ),
        ]
        indexes = [models.Index(fields=["farm", "ingredient", "-valid_from"])]

    def __str__(self):
        return f"{self.ingredient} — {self.price_per_kg_as_fed} {self.currency}/kg ({self.valid_from})"

    def clean(self):
        if self.ingredient_id and self.farm_id and self.ingredient.farm_id not in (None, self.farm_id):
            raise ValidationError({"ingredient": "Cet ingrédient privé appartient à une autre exploitation."})


class NutritionalReference(ValidatedReferenceModel):
    """Ensemble de besoins documentés pour un profil d'animal, dans un système nutritionnel donné."""

    name = models.CharField("intitulé", max_length=200)
    species = models.ForeignKey(
        "animals.Species", on_delete=models.PROTECT, related_name="nutritional_references"
    )
    breed = models.ForeignKey(
        "animals.Breed", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    category = models.ForeignKey(
        "animals.AnimalCategory", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    physiological_stage = models.ForeignKey(
        "animals.PhysiologicalStage", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    objective = models.ForeignKey(
        "animals.ProductionObjective", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # Besoins propres à une saison (ex. chaleur : ingestion réduite) ; vide = toute l'année.
    season = models.ForeignKey(
        "seasons.Season", on_delete=models.PROTECT, null=True, blank=True, related_name="references"
    )
    system = models.ForeignKey(NutritionSystem, on_delete=models.PROTECT, related_name="references")
    age_min_months = models.DecimalField(
        "âge min. (mois)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    age_max_months = models.DecimalField(
        "âge max. (mois)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    weight_min_kg = models.DecimalField(
        "poids min. (kg)", max_digits=7, decimal_places=2, null=True, blank=True
    )
    weight_max_kg = models.DecimalField(
        "poids max. (kg)", max_digits=7, decimal_places=2, null=True, blank=True
    )
    dm_intake_min_kg_day = models.DecimalField(
        "ingestion de MS min. (kg/j)", max_digits=6, decimal_places=3, null=True, blank=True
    )
    dm_intake_max_kg_day = models.DecimalField(
        "ingestion de MS max. (kg/j)", max_digits=6, decimal_places=3, null=True, blank=True
    )
    application_conditions = models.TextField("conditions d'application", blank=True)
    notes = models.TextField("notes", blank=True)

    class Meta:
        verbose_name = "référence nutritionnelle"
        verbose_name_plural = "références nutritionnelles"
        ordering = ["species__name", "name"]
        constraints = [
            *validated_reference_constraints(),
            models.CheckConstraint(
                condition=Q(age_min_months__isnull=True)
                | Q(age_max_months__isnull=True)
                | Q(age_min_months__lte=models.F("age_max_months")),
                name="reference_age_range_ordered",
            ),
            models.CheckConstraint(
                condition=Q(weight_min_kg__isnull=True)
                | Q(weight_max_kg__isnull=True)
                | Q(weight_min_kg__lte=models.F("weight_max_kg")),
                name="reference_weight_range_ordered",
            ),
            models.CheckConstraint(
                condition=Q(dm_intake_min_kg_day__isnull=True)
                | Q(dm_intake_max_kg_day__isnull=True)
                | Q(dm_intake_min_kg_day__lte=models.F("dm_intake_max_kg_day")),
                name="reference_intake_range_ordered",
            ),
            models.CheckConstraint(
                condition=(Q(dm_intake_min_kg_day__isnull=True) | Q(dm_intake_min_kg_day__gt=0))
                & (Q(weight_min_kg__isnull=True) | Q(weight_min_kg__gt=0)),
                name="reference_values_positive",
            ),
        ]

    def __str__(self):
        return f"{self.name} [{self.system.code}]"

    def extra_validation_blockers(self):
        """Une référence sans aucun besoin chiffré ne peut pas être validée."""
        if not self.requirements.exists():
            return ["La référence ne contient aucun besoin nutritionnel."]
        return []

    def clean(self):
        errors = {}
        for field in ("breed", "category", "physiological_stage"):
            related = getattr(self, field, None) if getattr(self, f"{field}_id") else None
            if related is not None and self.species_id and related.species_id != self.species_id:
                errors[field] = "Ne correspond pas à l'espèce de la référence."
        if errors:
            raise ValidationError(errors)


class RequirementExpression(models.TextChoices):
    DAILY_AMOUNT = "DAILY_AMOUNT", "Quantité par animal et par jour"
    DIET_CONCENTRATION = "DIET_CONCENTRATION", "Teneur de la ration (par kg de MS)"


class NutritionalRequirement(TimeStampedModel):
    reference = models.ForeignKey(NutritionalReference, on_delete=models.CASCADE, related_name="requirements")
    nutrient = models.ForeignKey(Nutrient, on_delete=models.PROTECT, related_name="requirements")
    expression = models.CharField("expression", max_length=24, choices=RequirementExpression.choices)
    min_value = models.DecimalField("minimum", max_digits=12, decimal_places=4, null=True, blank=True)
    target_value = models.DecimalField("cible", max_digits=12, decimal_places=4, null=True, blank=True)
    max_value = models.DecimalField("maximum", max_digits=12, decimal_places=4, null=True, blank=True)
    notes = models.TextField("notes", blank=True)

    class Meta:
        verbose_name = "besoin nutritionnel"
        verbose_name_plural = "besoins nutritionnels"
        ordering = ["reference", "nutrient__sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["reference", "nutrient", "expression"], name="requirement_unique_per_reference"
            ),
            models.CheckConstraint(
                condition=Q(min_value__isnull=False)
                | Q(target_value__isnull=False)
                | Q(max_value__isnull=False),
                name="requirement_has_a_value",
            ),
            models.CheckConstraint(
                condition=(Q(min_value__isnull=True) | Q(min_value__gte=0))
                & (Q(target_value__isnull=True) | Q(target_value__gte=0))
                & (Q(max_value__isnull=True) | Q(max_value__gte=0)),
                name="requirement_values_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(min_value__isnull=True)
                | Q(max_value__isnull=True)
                | Q(min_value__lte=models.F("max_value")),
                name="requirement_min_le_max",
            ),
            models.CheckConstraint(
                condition=Q(min_value__isnull=True)
                | Q(target_value__isnull=True)
                | Q(min_value__lte=models.F("target_value")),
                name="requirement_min_le_target",
            ),
            models.CheckConstraint(
                condition=Q(target_value__isnull=True)
                | Q(max_value__isnull=True)
                | Q(target_value__lte=models.F("max_value")),
                name="requirement_target_le_max",
            ),
        ]

    def __str__(self):
        return f"{self.reference} — {self.nutrient.code}"

    @property
    def unit_label(self) -> str:
        if self.expression == RequirementExpression.DAILY_AMOUNT:
            return f"{self.nutrient.amount_unit}/jour"
        return self.nutrient.unit_label

    def clean(self):
        if not (self.nutrient_id and self.reference_id):
            return
        if self.nutrient.system_id and self.nutrient.system_id != self.reference.system_id:
            raise ValidationError(
                {
                    "nutrient": (
                        f"Le nutriment {self.nutrient.code} appartient au système "
                        f"« {self.nutrient.system} », "
                        f"incompatible avec la référence exprimée dans « {self.reference.system} »."
                    )
                }
            )
        if (
            self.nutrient.category == NutrientCategory.DRY_MATTER
            and self.expression == RequirementExpression.DAILY_AMOUNT
        ):
            raise ValidationError(
                {
                    "expression": (
                        "L'ingestion de matière sèche se renseigne dans les bornes "
                        "d'ingestion de la référence."
                    )
                }
            )


class InclusionConstraint(ValidatedReferenceModel):
    """Borne d'incorporation d'un ingrédient (ou d'une catégorie) dans la ration, configurée par un expert."""

    species = models.ForeignKey("animals.Species", on_delete=models.PROTECT, related_name="+")
    animal_category = models.ForeignKey(
        "animals.AnimalCategory", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, null=True, blank=True, related_name="inclusion_constraints"
    )
    ingredient_category = models.ForeignKey(
        IngredientCategory,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="inclusion_constraints",
    )
    min_pct_dm = models.DecimalField(
        "incorporation min. (% MS)", max_digits=5, decimal_places=2, null=True, blank=True
    )
    max_pct_dm = models.DecimalField(
        "incorporation max. (% MS)", max_digits=5, decimal_places=2, null=True, blank=True
    )
    rationale = models.TextField("justification", blank=True)

    class Meta:
        verbose_name = "contrainte d'incorporation"
        verbose_name_plural = "contraintes d'incorporation"
        constraints = [
            *validated_reference_constraints(),
            models.CheckConstraint(
                condition=Q(ingredient__isnull=False, ingredient_category__isnull=True)
                | Q(ingredient__isnull=True, ingredient_category__isnull=False),
                name="inclusion_targets_ingredient_xor_category",
            ),
            models.CheckConstraint(
                condition=Q(min_pct_dm__isnull=False) | Q(max_pct_dm__isnull=False),
                name="inclusion_has_a_bound",
            ),
            models.CheckConstraint(
                condition=(Q(min_pct_dm__isnull=True) | Q(min_pct_dm__gte=0, min_pct_dm__lte=100))
                & (Q(max_pct_dm__isnull=True) | Q(max_pct_dm__gte=0, max_pct_dm__lte=100)),
                name="inclusion_bounds_are_percentages",
            ),
            models.CheckConstraint(
                condition=Q(min_pct_dm__isnull=True)
                | Q(max_pct_dm__isnull=True)
                | Q(min_pct_dm__lte=models.F("max_pct_dm")),
                name="inclusion_min_le_max",
            ),
        ]

    def __str__(self):
        target = self.ingredient or self.ingredient_category
        return f"{target} : {self.min_pct_dm or 0} – {self.max_pct_dm or 100} % MS"


__all__ = [
    "AmountUnit",
    "ExpressionBasis",
    "InclusionConstraint",
    "Ingredient",
    "IngredientCategory",
    "IngredientComposition",
    "IngredientPrice",
    "Nutrient",
    "NutrientCategory",
    "NutritionSystem",
    "NutritionalReference",
    "NutritionalRequirement",
    "RequirementExpression",
    "ValidationStatus",
]
