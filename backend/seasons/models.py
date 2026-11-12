"""
Module « Saison » : calendrier des saisons, disponibilité des aliments par saison (déclarée par la ferme)
et conseils de saison (validés par un spécialiste avant d'être montrés aux éleveurs).

Les prix par saison sont des prix d'ingrédients rattachés à une saison (`nutrition.IngredientPrice.season`) ;
les besoins propres à une saison (chaleur…) sont des références nutritionnelles rattachées à une saison
(`nutrition.NutritionalReference.season`), validées comme toute référence. Rien n'est inventé : sans donnée
validée, le calcul reste celui de toute l'année.
"""

from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel
from governance.models import ValidatedReferenceModel, validated_reference_constraints


class Season(TimeStampedModel):
    """Période de l'année (calendrier indicatif, ajustable par un administrateur selon la zone)."""

    code = models.CharField("code", max_length=32, unique=True)
    name = models.CharField("nom", max_length=120)
    start_month = models.PositiveSmallIntegerField("premier mois (1-12)")
    end_month = models.PositiveSmallIntegerField("dernier mois (1-12)")
    is_hot = models.BooleanField("saison chaude", default=False)
    description = models.TextField("description", blank=True)
    sort_order = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "saison"
        verbose_name_plural = "saisons"
        ordering = ["sort_order", "name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(start_month__gte=1, start_month__lte=12, end_month__gte=1, end_month__lte=12),
                name="season_months_valid",
            )
        ]

    def __str__(self):
        return self.name

    def contains(self, month: int) -> bool:
        if self.start_month <= self.end_month:
            return self.start_month <= month <= self.end_month
        return month >= self.start_month or month <= self.end_month  # saison à cheval sur l'année

    def months(self) -> list[int]:
        return [m for m in range(1, 13) if self.contains(m)]

    @classmethod
    def for_date(cls, day: date | None = None):
        day = day or date.today()
        return next((s for s in cls.objects.all() if s.contains(day.month)), None)


class AvailabilityLevel(models.TextChoices):
    ABUNDANT = "ABUNDANT", "Abondant"
    AVAILABLE = "AVAILABLE", "Disponible"
    SCARCE = "SCARCE", "Rare"
    UNAVAILABLE = "UNAVAILABLE", "Indisponible"


class IngredientAvailability(TimeStampedModel):
    """Disponibilité d'un aliment pour une exploitation pendant une saison (déclarée par l'éleveur)."""

    farm = models.ForeignKey("farms.Farm", on_delete=models.CASCADE, related_name="ingredient_availabilities")
    ingredient = models.ForeignKey("nutrition.Ingredient", on_delete=models.CASCADE, related_name="+")
    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name="availabilities")
    level = models.CharField("disponibilité", max_length=16, choices=AvailabilityLevel.choices)
    notes = models.TextField("notes", blank=True)
    is_demo = models.BooleanField("donnée DEMO", default=False, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "disponibilité saisonnière"
        verbose_name_plural = "disponibilités saisonnières"
        constraints = [
            models.UniqueConstraint(
                fields=["farm", "ingredient", "season"], name="availability_unique_per_farm_season"
            )
        ]

    def __str__(self):
        return f"{self.ingredient} — {self.season} : {self.get_level_display()}"

    def clean(self):
        if self.ingredient_id and self.farm_id and self.ingredient.farm_id not in (None, self.farm_id):
            raise ValidationError({"ingredient": "Cet ingrédient appartient à une autre exploitation."})


class AdviceTopic(models.TextChoices):
    WATER = "WATER", "Eau"
    FEED = "FEED", "Alimentation"
    SCHEDULE = "SCHEDULE", "Horaires"
    HOUSING = "HOUSING", "Abri et ombre"
    OTHER = "OTHER", "Autre"


class SeasonalAdvice(ValidatedReferenceModel):
    """Conseil pratique de saison : montré aux éleveurs seulement après validation par un spécialiste."""

    season = models.ForeignKey(Season, on_delete=models.PROTECT, related_name="advice")
    species = models.ForeignKey(
        "animals.Species", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    topic = models.CharField("thème", max_length=16, choices=AdviceTopic.choices, default=AdviceTopic.OTHER)
    title = models.CharField("titre", max_length=200)
    text = models.TextField("conseil")

    class Meta:
        verbose_name = "conseil de saison"
        verbose_name_plural = "conseils de saison"
        ordering = ["season__sort_order", "topic", "title"]
        constraints = [*validated_reference_constraints()]

    def __str__(self):
        return self.title
