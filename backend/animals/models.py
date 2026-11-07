"""
Espèces, races, catégories, stades physiologiques, lots et animaux.

Les espèces et leurs nomenclatures (catégories, stades) sont des tables : ajouter les caprins
ou les bovins consiste à activer l'espèce et à saisir ses nomenclatures, sans modifier le code.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models import TimeStampedModel


class Species(TimeStampedModel):
    code = models.CharField("code", max_length=32, unique=True)
    name = models.CharField("nom", max_length=100)
    scientific_name = models.CharField("nom scientifique", max_length=150, blank=True)
    is_active = models.BooleanField(
        "active", default=True, help_text="Seules les espèces actives sont proposées aux éleveurs."
    )

    class Meta:
        verbose_name = "espèce"
        verbose_name_plural = "espèces"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Breed(TimeStampedModel):
    species = models.ForeignKey(Species, on_delete=models.PROTECT, related_name="breeds")
    name = models.CharField("nom", max_length=120)
    local_names = models.CharField("autres appellations", max_length=255, blank=True)
    description = models.TextField("description", blank=True)
    is_active = models.BooleanField("active", default=True)

    class Meta:
        verbose_name = "race"
        verbose_name_plural = "races"
        ordering = ["species__name", "name"]
        constraints = [models.UniqueConstraint(fields=["species", "name"], name="breed_unique_per_species")]

    def __str__(self):
        return self.name


class AnimalCategory(TimeStampedModel):
    species = models.ForeignKey(Species, on_delete=models.PROTECT, related_name="categories")
    code = models.CharField("code", max_length=32)
    name = models.CharField("nom", max_length=120)
    description = models.TextField("description", blank=True)
    sort_order = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "catégorie d'animal"
        verbose_name_plural = "catégories d'animaux"
        ordering = ["species__name", "sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["species", "code"], name="animalcategory_unique_code_per_species")
        ]

    def __str__(self):
        return self.name


class PhysiologicalStage(TimeStampedModel):
    species = models.ForeignKey(Species, on_delete=models.PROTECT, related_name="stages")
    code = models.CharField("code", max_length=32)
    name = models.CharField("nom", max_length=120)
    description = models.TextField("description", blank=True)
    sort_order = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "stade physiologique"
        verbose_name_plural = "stades physiologiques"
        ordering = ["species__name", "sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["species", "code"], name="physiologicalstage_unique_code_per_species"
            )
        ]

    def __str__(self):
        return self.name


class ProductionObjective(TimeStampedModel):
    code = models.CharField("code", max_length=32, unique=True)
    name = models.CharField("nom", max_length=120)
    description = models.TextField("description", blank=True)
    sort_order = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "objectif de production"
        verbose_name_plural = "objectifs de production"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class AnimalGroup(TimeStampedModel):
    farm = models.ForeignKey("farms.Farm", on_delete=models.CASCADE, related_name="groups")
    name = models.CharField("nom du lot", max_length=150)
    species = models.ForeignKey(Species, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    description = models.TextField("description", blank=True)
    is_active = models.BooleanField("actif", default=True)
    is_demo = models.BooleanField("donnée DEMO", default=False, db_index=True)

    class Meta:
        verbose_name = "lot"
        verbose_name_plural = "lots"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["farm", "name"], name="animalgroup_unique_name_per_farm")
        ]

    def __str__(self):
        return self.name


class Sex(models.TextChoices):
    MALE = "M", "Mâle"
    FEMALE = "F", "Femelle"


class AnimalStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Présent"
    SOLD = "SOLD", "Vendu"
    DEAD = "DEAD", "Mort"
    ARCHIVED = "ARCHIVED", "Archivé"


class Animal(TimeStampedModel):
    uuid = models.UUIDField("identifiant unique", default=uuid.uuid4, unique=True, editable=False)
    farm = models.ForeignKey("farms.Farm", on_delete=models.CASCADE, related_name="animals")
    tag_number = models.CharField("numéro / boucle", max_length=64)
    name = models.CharField("nom", max_length=120, blank=True)
    species = models.ForeignKey(Species, on_delete=models.PROTECT, related_name="animals")
    breed = models.ForeignKey(Breed, on_delete=models.PROTECT, null=True, blank=True, related_name="animals")
    sex = models.CharField("sexe", max_length=1, choices=Sex.choices)
    birth_date = models.DateField("date de naissance", null=True, blank=True)
    birth_date_is_estimated = models.BooleanField(
        "date estimée", default=False, help_text="Cochée si la date est déduite d'un âge estimé."
    )
    initial_weight_kg = models.DecimalField(
        "poids initial (kg)", max_digits=7, decimal_places=2, null=True, blank=True
    )
    category = models.ForeignKey(
        AnimalCategory, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    physiological_stage = models.ForeignKey(
        PhysiologicalStage, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    group = models.ForeignKey(
        AnimalGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="animals"
    )
    registered_on = models.DateField("date d'enregistrement", default=timezone.localdate)
    observations = models.TextField("observations", blank=True)
    status = models.CharField(
        "statut", max_length=16, choices=AnimalStatus.choices, default=AnimalStatus.ACTIVE, db_index=True
    )
    archived_at = models.DateTimeField("archivé le", null=True, blank=True)
    is_demo = models.BooleanField("donnée DEMO", default=False, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "animal"
        verbose_name_plural = "animaux"
        ordering = ["tag_number"]
        constraints = [
            models.UniqueConstraint(fields=["farm", "tag_number"], name="animal_unique_tag_per_farm"),
            models.CheckConstraint(
                condition=Q(initial_weight_kg__isnull=True) | Q(initial_weight_kg__gt=0),
                name="animal_initial_weight_positive",
            ),
        ]
        indexes = [models.Index(fields=["farm", "species", "status"])]

    def __str__(self):
        return f"{self.tag_number} — {self.name}" if self.name else self.tag_number

    def clean(self):
        errors = {}
        if self.breed_id and self.species_id and self.breed.species_id != self.species_id:
            errors["breed"] = "La race ne correspond pas à l'espèce choisie."
        if self.category_id and self.species_id and self.category.species_id != self.species_id:
            errors["category"] = "La catégorie ne correspond pas à l'espèce choisie."
        if (
            self.physiological_stage_id
            and self.species_id
            and self.physiological_stage.species_id != self.species_id
        ):
            errors["physiological_stage"] = "Le stade physiologique ne correspond pas à l'espèce choisie."
        if self.group_id:
            if self.farm_id and self.group.farm_id != self.farm_id:
                errors["group"] = "Le lot appartient à une autre exploitation."
            elif self.group.species_id and self.species_id and self.group.species_id != self.species_id:
                errors["group"] = "Le lot est réservé à une autre espèce."
        if self.birth_date and self.birth_date > timezone.localdate():
            errors["birth_date"] = "La date de naissance ne peut pas être dans le futur."
        if errors:
            raise ValidationError(errors)

    def age_in_days(self, on_date=None):
        if not self.birth_date:
            return None
        return ((on_date or timezone.localdate()) - self.birth_date).days


class ObservationKind(models.TextChoices):
    GENERAL = "GENERAL", "Générale"
    FEEDING = "FEEDING", "Alimentation"
    BEHAVIOR = "BEHAVIOR", "Comportement"
    HEALTH = "HEALTH", "État de santé observé (non diagnostique)"
    REPRODUCTION = "REPRODUCTION", "Reproduction"
    OTHER = "OTHER", "Autre"


class AnimalObservation(TimeStampedModel):
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="observation_entries")
    observed_on = models.DateField("date", default=timezone.localdate)
    kind = models.CharField(
        "type", max_length=16, choices=ObservationKind.choices, default=ObservationKind.GENERAL
    )
    text = models.TextField("observation")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        verbose_name = "observation"
        verbose_name_plural = "observations"
        ordering = ["-observed_on", "-created_at"]

    def __str__(self):
        return f"{self.animal} — {self.observed_on}"
