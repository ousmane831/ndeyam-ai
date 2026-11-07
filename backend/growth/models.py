"""
Pesées et plages de suivi de croissance.

Les plages de suivi (GMD attendu) sont des données de référence : elles doivent être sourcées
et validées avant de déclencher des alertes. Ces alertes ne sont jamais des diagnostics vétérinaires.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from core.models import TimeStampedModel
from governance.models import ValidatedReferenceModel, validated_reference_constraints


class WeighingMethod(models.TextChoices):
    SCALE = "SCALE", "Balance / bascule"
    TAPE = "TAPE", "Ruban barymétrique"
    VISUAL = "VISUAL", "Estimation visuelle"


class Weighing(TimeStampedModel):
    animal = models.ForeignKey("animals.Animal", on_delete=models.CASCADE, related_name="weighings")
    weighed_on = models.DateField("date de pesée", default=timezone.localdate)
    weight_kg = models.DecimalField("poids (kg)", max_digits=7, decimal_places=2)
    method = models.CharField(
        "méthode", max_length=8, choices=WeighingMethod.choices, default=WeighingMethod.SCALE
    )
    observations = models.TextField("observations", blank=True)
    is_demo = models.BooleanField("donnée DEMO", default=False, db_index=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="saisi par",
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )

    UNIT = "kg"

    class Meta:
        verbose_name = "pesée"
        verbose_name_plural = "pesées"
        ordering = ["-weighed_on"]
        constraints = [
            models.UniqueConstraint(fields=["animal", "weighed_on"], name="weighing_one_per_animal_per_day"),
            models.CheckConstraint(condition=Q(weight_kg__gt=0), name="weighing_weight_positive"),
        ]
        indexes = [models.Index(fields=["animal", "weighed_on"])]

    def __str__(self):
        return f"{self.animal} — {self.weight_kg} kg le {self.weighed_on}"

    def clean(self):
        if self.weighed_on and self.weighed_on > timezone.localdate():
            raise ValidationError({"weighed_on": "La date de pesée ne peut pas être dans le futur."})
        if (
            self.animal_id
            and self.animal.birth_date
            and self.weighed_on
            and self.weighed_on < self.animal.birth_date
        ):
            raise ValidationError(
                {"weighed_on": "La pesée est antérieure à la date de naissance de l'animal."}
            )


class GrowthMonitoringRange(ValidatedReferenceModel):
    """Plage de gain moyen quotidien (GMD) attendue pour un profil d'animal, issue d'une source documentée."""

    name = models.CharField("intitulé", max_length=200)
    species = models.ForeignKey("animals.Species", on_delete=models.PROTECT, related_name="+")
    breed = models.ForeignKey(
        "animals.Breed", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    category = models.ForeignKey(
        "animals.AnimalCategory", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    physiological_stage = models.ForeignKey(
        "animals.PhysiologicalStage", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    sex = models.CharField("sexe", max_length=1, blank=True, choices=[("M", "Mâle"), ("F", "Femelle")])
    age_min_days = models.PositiveIntegerField("âge min. (jours)", null=True, blank=True)
    age_max_days = models.PositiveIntegerField("âge max. (jours)", null=True, blank=True)
    adg_min_g = models.DecimalField("GMD min. (g/j)", max_digits=7, decimal_places=1, null=True, blank=True)
    adg_max_g = models.DecimalField("GMD max. (g/j)", max_digits=7, decimal_places=1, null=True, blank=True)
    notes = models.TextField("notes", blank=True)

    class Meta:
        verbose_name = "plage de suivi de croissance"
        verbose_name_plural = "plages de suivi de croissance"
        constraints = [
            *validated_reference_constraints(),
            models.CheckConstraint(
                condition=Q(adg_min_g__isnull=False) | Q(adg_max_g__isnull=False),
                name="growthrange_has_a_bound",
            ),
            models.CheckConstraint(
                condition=Q(adg_min_g__isnull=True)
                | Q(adg_max_g__isnull=True)
                | Q(adg_min_g__lte=F("adg_max_g")),
                name="growthrange_min_le_max",
            ),
            models.CheckConstraint(
                condition=Q(age_min_days__isnull=True)
                | Q(age_max_days__isnull=True)
                | Q(age_min_days__lte=F("age_max_days")),
                name="growthrange_age_ordered",
            ),
        ]

    def __str__(self):
        return self.name
