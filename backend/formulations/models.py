"""
Formulations d'aliments.

Une formule conserve un instantané complet du calcul (`result_snapshot`) : apports estimés,
comparaison aux besoins, statut de chaque contrainte, sources utilisées et avertissements.
Le résultat reste une ESTIMATION MATHÉMATIQUE tant qu'un expert ne l'a pas validé.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel
from governance.models import ValidatedReferenceModel, validated_reference_constraints


class FormulaMode(models.TextChoices):
    ECONOMIC = "ECONOMIC", "Économique (coût minimal)"
    BALANCED = "BALANCED", "Équilibré (objectifs nutritionnels)"
    MANUAL = "MANUAL", "Saisie manuelle"
    TEMPLATE = "TEMPLATE", "Ration type"


class FormulaStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    REFUSED = "REFUSED", "Calcul refusé (données insuffisantes)"
    INFEASIBLE = "INFEASIBLE", "Aucune solution (contraintes incompatibles)"
    ESTIMATED = "ESTIMATED", "Estimation mathématique"
    PENDING_REVIEW = "PENDING_REVIEW", "En attente de vérification"
    VALIDATED = "VALIDATED", "Validée par un expert"
    REJECTED = "REJECTED", "Rejetée par un expert"


class FeedFormula(TimeStampedModel):
    farm = models.ForeignKey("farms.Farm", on_delete=models.CASCADE, related_name="formulas")
    name = models.CharField("nom", max_length=200)
    species = models.ForeignKey("animals.Species", on_delete=models.PROTECT, related_name="+")
    reference = models.ForeignKey(
        "nutrition.NutritionalReference",
        verbose_name="référence nutritionnelle utilisée",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="formulas",
    )
    mode = models.CharField("mode", max_length=16, choices=FormulaMode.choices)
    status = models.CharField(
        "statut", max_length=16, choices=FormulaStatus.choices, default=FormulaStatus.DRAFT, db_index=True
    )
    is_demo = models.BooleanField("donnée DEMO", default=False, db_index=True)
    # Profil de l'animal visé
    animal = models.ForeignKey(
        "animals.Animal", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    group = models.ForeignKey(
        "animals.AnimalGroup", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    season = models.ForeignKey(
        "seasons.Season", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    animal_weight_kg = models.DecimalField(
        "poids (kg)", max_digits=7, decimal_places=2, null=True, blank=True
    )
    animal_age_months = models.DecimalField(
        "âge (mois)", max_digits=5, decimal_places=1, null=True, blank=True
    )
    physiological_stage = models.ForeignKey(
        "animals.PhysiologicalStage", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    objective = models.ForeignKey(
        "animals.ProductionObjective", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # Résultats
    dm_intake_kg_day = models.DecimalField(
        "MS ingérée (kg/animal/j)", max_digits=7, decimal_places=3, null=True, blank=True
    )
    as_fed_kg_day = models.DecimalField(
        "aliment brut (kg/animal/j)", max_digits=7, decimal_places=3, null=True, blank=True
    )
    cost_per_day = models.DecimalField(
        "coût (par animal et par jour)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    cost_per_kg_as_fed = models.DecimalField(
        "coût par kg brut", max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField("devise", max_length=3, default="XOF")
    result_snapshot = models.JSONField("détail du calcul", default=dict, blank=True)
    warnings = models.JSONField("avertissements", default=list, blank=True)
    solver_status = models.CharField("statut du solveur", max_length=64, blank=True)
    engine_version = models.CharField("version du moteur", max_length=32, blank=True)
    # Validation humaine
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    validated_at = models.DateTimeField("validée le", null=True, blank=True)
    review_comment = models.TextField("commentaire de l'expert", blank=True)
    review_requested_at = models.DateTimeField("vérification demandée le", null=True, blank=True)
    template = models.ForeignKey(
        "RationTemplate", on_delete=models.SET_NULL, null=True, blank=True, related_name="formulas"
    )
    notes = models.TextField("notes", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "formule"
        verbose_name_plural = "formules"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(is_demo=True, status="VALIDATED"), name="formula_demo_never_validated"
            ),
            models.CheckConstraint(
                condition=~Q(status="VALIDATED") | Q(validated_at__isnull=False),
                name="formula_validated_has_date",
            ),
            models.CheckConstraint(
                condition=Q(animal_weight_kg__isnull=True) | Q(animal_weight_kg__gt=0),
                name="formula_weight_positive",
            ),
        ]
        indexes = [models.Index(fields=["farm", "status", "-created_at"])]

    def __str__(self):
        return self.name


class FeedFormulaIngredient(models.Model):
    formula = models.ForeignKey(FeedFormula, on_delete=models.CASCADE, related_name="items")
    ingredient = models.ForeignKey("nutrition.Ingredient", on_delete=models.PROTECT, related_name="+")
    inclusion_pct_dm = models.DecimalField(
        "part dans la MS (%)",
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Vide si la matière sèche d'un ingrédient n'est pas connue (validée).",
    )
    inclusion_pct_as_fed = models.DecimalField(
        "part dans le brut (%)", max_digits=6, decimal_places=3, null=True, blank=True
    )
    quantity_dm_kg = models.DecimalField(
        "quantité de MS (kg/animal/j)", max_digits=9, decimal_places=4, null=True, blank=True
    )
    quantity_as_fed_kg = models.DecimalField(
        "quantité brute (kg/animal/j)", max_digits=9, decimal_places=4, null=True, blank=True
    )
    price = models.ForeignKey(
        "nutrition.IngredientPrice", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    price_per_kg_as_fed = models.DecimalField(
        "prix appliqué (par kg brut)", max_digits=12, decimal_places=2, null=True, blank=True
    )
    cost_per_day = models.DecimalField(
        "coût (par animal et par jour)", max_digits=12, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = "ingrédient de la formule"
        verbose_name_plural = "ingrédients de la formule"
        ordering = ["-inclusion_pct_dm"]
        constraints = [
            models.UniqueConstraint(fields=["formula", "ingredient"], name="formulaitem_unique_ingredient"),
            models.CheckConstraint(
                condition=Q(inclusion_pct_dm__isnull=True)
                | Q(inclusion_pct_dm__gte=0, inclusion_pct_dm__lte=100),
                name="formulaitem_pct_dm_range",
            ),
            models.CheckConstraint(
                condition=Q(quantity_dm_kg__isnull=False) | Q(quantity_as_fed_kg__isnull=False),
                name="formulaitem_has_a_quantity",
            ),
            models.CheckConstraint(
                condition=Q(inclusion_pct_as_fed__isnull=True)
                | Q(inclusion_pct_as_fed__gte=0, inclusion_pct_as_fed__lte=100),
                name="formulaitem_pct_as_fed_range",
            ),
            models.CheckConstraint(
                condition=(Q(quantity_dm_kg__isnull=True) | Q(quantity_dm_kg__gte=0))
                & (Q(quantity_as_fed_kg__isnull=True) | Q(quantity_as_fed_kg__gte=0)),
                name="formulaitem_quantities_non_negative",
            ),
        ]

    def __str__(self):
        if self.inclusion_pct_dm is not None:
            return f"{self.ingredient} — {self.inclusion_pct_dm} % MS"
        return f"{self.ingredient} — {self.quantity_as_fed_kg} kg brut"


class RationTemplate(ValidatedReferenceModel):
    """
    Ration type : proportions d'aliments (part de la matière sèche) et ingestion journalière, validées UNE
    FOIS par un expert pour un cas courant (espèce, catégorie, stade, objectif, saison, tranche de poids).
    L'éleveur qui se trouve dans ce cas l'applique immédiatement : seules les quantités brutes et le coût
    sont recalculés, avec ses données (matière sèche validée des aliments, prix du jour). Les apports
    nutritionnels ne changent pas.
    """

    name = models.CharField("nom", max_length=200)
    species = models.ForeignKey("animals.Species", on_delete=models.PROTECT, related_name="+")
    category = models.ForeignKey(
        "animals.AnimalCategory", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    physiological_stage = models.ForeignKey(
        "animals.PhysiologicalStage", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    objective = models.ForeignKey(
        "animals.ProductionObjective", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    season = models.ForeignKey(
        "seasons.Season", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    weight_min_kg = models.DecimalField("poids min. (kg)", max_digits=7, decimal_places=2)
    weight_max_kg = models.DecimalField("poids max. (kg)", max_digits=7, decimal_places=2)
    dm_intake_kg_day = models.DecimalField(
        "matière sèche par animal et par jour (kg)", max_digits=6, decimal_places=3
    )
    conditions = models.TextField("conditions d'emploi", blank=True)
    origin_formula = models.ForeignKey(
        FeedFormula, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "ration type"
        verbose_name_plural = "rations types"
        ordering = ["name"]
        constraints = [
            *validated_reference_constraints(),
            models.CheckConstraint(condition=Q(weight_min_kg__gt=0), name="template_weight_positive"),
            models.CheckConstraint(
                condition=Q(weight_min_kg__lte=models.F("weight_max_kg")), name="template_weight_ordered"
            ),
            models.CheckConstraint(condition=Q(dm_intake_kg_day__gt=0), name="template_intake_positive"),
        ]

    def __str__(self):
        return self.name


class RationTemplateItem(models.Model):
    template = models.ForeignKey(RationTemplate, on_delete=models.CASCADE, related_name="items")
    ingredient = models.ForeignKey("nutrition.Ingredient", on_delete=models.PROTECT, related_name="+")
    inclusion_pct_dm = models.DecimalField("part dans la MS (%)", max_digits=6, decimal_places=3)

    class Meta:
        verbose_name = "aliment de la ration type"
        verbose_name_plural = "aliments de la ration type"
        ordering = ["-inclusion_pct_dm"]
        constraints = [
            models.UniqueConstraint(fields=["template", "ingredient"], name="templateitem_unique_ingredient"),
            models.CheckConstraint(
                condition=Q(inclusion_pct_dm__gt=0, inclusion_pct_dm__lte=100), name="templateitem_pct_range"
            ),
        ]

    def __str__(self):
        return f"{self.ingredient} : {self.inclusion_pct_dm} % de la MS"
