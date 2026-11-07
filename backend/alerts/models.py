"""
Alertes et rappels.

Chaque alerte est explicable et traçable : elle conserve le code de la règle qui l'a produite
et les valeurs qui l'ont déclenchée (`trigger_data`). Elle peut pointer vers l'objet concerné.
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel


class AlertType(models.TextChoices):
    WEIGHING_REMINDER = "WEIGHING_REMINDER", "Rappel de pesée"
    FOLLOW_UP_REMINDER = "FOLLOW_UP_REMINDER", "Rappel de suivi"
    MISSING_DATA = "MISSING_DATA", "Information manquante"
    REFERENCE_TO_VALIDATE = "REFERENCE_TO_VALIDATE", "Donnée de référence à valider"
    FORMULA_TO_REVIEW = "FORMULA_TO_REVIEW", "Formulation à vérifier"
    GROWTH_OUT_OF_RANGE = "GROWTH_OUT_OF_RANGE", "Croissance hors plage de suivi"


class AlertSeverity(models.TextChoices):
    INFO = "INFO", "Information"
    WARNING = "WARNING", "Attention"
    CRITICAL = "CRITICAL", "Important"


class AlertStatus(models.TextChoices):
    OPEN = "OPEN", "Ouverte"
    ACKNOWLEDGED = "ACKNOWLEDGED", "Prise en compte"
    RESOLVED = "RESOLVED", "Résolue"
    DISMISSED = "DISMISSED", "Ignorée"


class AlertRule(TimeStampedModel):
    farm = models.ForeignKey(
        "farms.Farm",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alert_rules",
        help_text="Vide = règle par défaut de la plateforme.",
    )
    alert_type = models.CharField("type", max_length=32, choices=AlertType.choices)
    name = models.CharField("nom", max_length=200)
    description = models.TextField("description", blank=True)
    parameters = models.JSONField("paramètres", default=dict, blank=True)
    is_active = models.BooleanField("active", default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "règle d'alerte"
        verbose_name_plural = "règles d'alerte"
        ordering = ["alert_type", "name"]
        constraints = [
            # Une règle par type et par exploitation (et une seule règle par défaut, sans exploitation).
            models.UniqueConstraint(
                fields=["farm", "alert_type"], nulls_distinct=False, name="alertrule_unique_type_per_farm"
            ),
        ]

    def __str__(self):
        return self.name


class Alert(TimeStampedModel):
    farm = models.ForeignKey(
        "farms.Farm", on_delete=models.CASCADE, null=True, blank=True, related_name="alerts"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="alerts"
    )
    alert_type = models.CharField("type", max_length=32, choices=AlertType.choices, db_index=True)
    severity = models.CharField(
        "niveau", max_length=8, choices=AlertSeverity.choices, default=AlertSeverity.INFO
    )
    title = models.CharField("titre", max_length=255)
    message = models.TextField("message")
    rule = models.ForeignKey(
        AlertRule, on_delete=models.SET_NULL, null=True, blank=True, related_name="alerts"
    )
    rule_code = models.CharField("code de la règle", max_length=64)
    trigger_data = models.JSONField("valeurs déclenchantes", default=dict, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    dedup_key = models.CharField("clé d'unicité", max_length=255)
    status = models.CharField(
        max_length=16, choices=AlertStatus.choices, default=AlertStatus.OPEN, db_index=True
    )
    due_date = models.DateField("échéance", null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "alerte"
        verbose_name_plural = "alertes"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(farm__isnull=False) | Q(recipient__isnull=False), name="alert_has_audience"
            ),
            # Pas de doublon d'alerte ouverte pour la même cause.
            models.UniqueConstraint(
                fields=["dedup_key"],
                condition=Q(status__in=["OPEN", "ACKNOWLEDGED"]),
                name="alert_unique_open_cause",
            ),
        ]
        indexes = [models.Index(fields=["farm", "status", "-created_at"])]

    def __str__(self):
        return self.title
