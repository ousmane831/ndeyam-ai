"""
Rations et enregistrements d'alimentation.

On distingue strictement trois quantités :
  - calculée   : issue de la formule (ce qu'il faudrait distribuer) ;
  - distribuée : réellement mise à disposition des animaux ;
  - consommée  : réellement ingérée, si elle a été mesurée (sinon vide, jamais déduite).
"""

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from core.models import TimeStampedModel

ONE_TARGET = Q(animal__isnull=False, group__isnull=True) | Q(animal__isnull=True, group__isnull=False)


class RationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "En cours"
    ENDED = "ENDED", "Terminée"


class Ration(TimeStampedModel):
    farm = models.ForeignKey("farms.Farm", on_delete=models.CASCADE, related_name="rations")
    name = models.CharField("nom", max_length=200)
    formula = models.ForeignKey("formulations.FeedFormula", on_delete=models.PROTECT, related_name="rations")
    animal = models.ForeignKey(
        "animals.Animal", on_delete=models.CASCADE, null=True, blank=True, related_name="rations"
    )
    group = models.ForeignKey(
        "animals.AnimalGroup", on_delete=models.CASCADE, null=True, blank=True, related_name="rations"
    )
    start_date = models.DateField("date de début", default=timezone.localdate)
    end_date = models.DateField("date de fin", null=True, blank=True)
    planned_as_fed_kg_per_animal_day = models.DecimalField(
        "quantité prévue (kg brut/animal/j)", max_digits=7, decimal_places=3, null=True, blank=True
    )
    status = models.CharField(
        max_length=8, choices=RationStatus.choices, default=RationStatus.ACTIVE, db_index=True
    )
    is_demo = models.BooleanField("donnée DEMO", default=False, db_index=True)
    notes = models.TextField("notes", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "ration"
        verbose_name_plural = "rations"
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(condition=ONE_TARGET, name="ration_targets_animal_xor_group"),
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="ration_dates_ordered",
            ),
            models.CheckConstraint(
                condition=Q(planned_as_fed_kg_per_animal_day__isnull=True)
                | Q(planned_as_fed_kg_per_animal_day__gt=0),
                name="ration_planned_quantity_positive",
            ),
        ]

    def __str__(self):
        return self.name


class FeedingRecord(TimeStampedModel):
    farm = models.ForeignKey("farms.Farm", on_delete=models.CASCADE, related_name="feeding_records")
    ration = models.ForeignKey(
        Ration, on_delete=models.SET_NULL, null=True, blank=True, related_name="records"
    )
    animal = models.ForeignKey(
        "animals.Animal", on_delete=models.CASCADE, null=True, blank=True, related_name="feeding_records"
    )
    group = models.ForeignKey(
        "animals.AnimalGroup", on_delete=models.CASCADE, null=True, blank=True, related_name="feeding_records"
    )
    fed_on = models.DateField("date", default=timezone.localdate)
    number_of_animals = models.PositiveIntegerField("nombre d'animaux nourris", null=True, blank=True)
    quantity_calculated_kg = models.DecimalField(
        "quantité calculée (kg brut)", max_digits=10, decimal_places=3, null=True, blank=True
    )
    quantity_distributed_kg = models.DecimalField(
        "quantité distribuée (kg brut)", max_digits=10, decimal_places=3
    )
    quantity_consumed_kg = models.DecimalField(
        "quantité consommée mesurée (kg brut)",
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="À renseigner uniquement si elle a été mesurée (pesée des refus). Jamais déduite.",
    )
    quantity_refused_kg = models.DecimalField(
        "refus pesés (kg brut)", max_digits=10, decimal_places=3, null=True, blank=True
    )
    estimated_cost = models.DecimalField(
        "coût estimé", max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField("devise", max_length=3, default="XOF")
    notes = models.TextField("notes", blank=True)
    is_demo = models.BooleanField("donnée DEMO", default=False, db_index=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        verbose_name = "distribution d'aliment"
        verbose_name_plural = "historique alimentaire"
        ordering = ["-fed_on", "-created_at"]
        constraints = [
            models.CheckConstraint(condition=ONE_TARGET, name="feeding_targets_animal_xor_group"),
            models.CheckConstraint(
                condition=Q(quantity_distributed_kg__gte=0)
                & (Q(quantity_calculated_kg__isnull=True) | Q(quantity_calculated_kg__gte=0))
                & (Q(quantity_consumed_kg__isnull=True) | Q(quantity_consumed_kg__gte=0))
                & (Q(quantity_refused_kg__isnull=True) | Q(quantity_refused_kg__gte=0)),
                name="feeding_quantities_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_consumed_kg__isnull=True)
                | Q(quantity_consumed_kg__lte=F("quantity_distributed_kg")),
                name="feeding_consumed_le_distributed",
            ),
            models.CheckConstraint(
                condition=Q(quantity_refused_kg__isnull=True)
                | Q(quantity_refused_kg__lte=F("quantity_distributed_kg")),
                name="feeding_refused_le_distributed",
            ),
        ]
        indexes = [models.Index(fields=["farm", "-fed_on"])]

    def __str__(self):
        return f"{self.fed_on} — {self.quantity_distributed_kg} kg"
