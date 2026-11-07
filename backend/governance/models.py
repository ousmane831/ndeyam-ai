"""
Gouvernance et traçabilité des données.

- SourceDocument : source bibliographique ou technique identifiable (table de composition,
  article, analyse de laboratoire…). Toute donnée de référence validée doit y être rattachée.
- ValidatedReferenceModel : base abstraite de toute donnée de référence (compositions, besoins,
  plages de suivi, documents RAG…). Elle impose, au niveau de PostgreSQL :
    * qu'une donnée DEMO ne puisse jamais être validée ;
    * qu'une donnée validée possède une source et une date de validation.
- ValidationRecord : historique de chaque décision de validation (qui, quand, quoi, pourquoi).
- ImportBatch : historique des importations CSV.
- ActivityLog : journal d'activité de la plateforme.
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel


class ValidationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Brouillon"
    PENDING = "PENDING", "En attente de validation"
    VALIDATED = "VALIDATED", "Validé"
    REJECTED = "REJECTED", "Rejeté"


class SourceType(models.TextChoices):
    COMPOSITION_TABLE = "COMPOSITION_TABLE", "Table de composition / référentiel"
    BOOK = "BOOK", "Ouvrage"
    ARTICLE = "ARTICLE", "Article scientifique"
    REPORT = "REPORT", "Rapport technique"
    LAB_ANALYSIS = "LAB_ANALYSIS", "Analyse de laboratoire"
    FIELD_SURVEY = "FIELD_SURVEY", "Enquête / mesure de terrain"
    EXPERT_OPINION = "EXPERT_OPINION", "Avis d'expert documenté"
    WEBSITE = "WEBSITE", "Site web / base en ligne"
    OTHER = "OTHER", "Autre"


class SourceDocument(TimeStampedModel):
    title = models.CharField("titre", max_length=300)
    authors = models.CharField("auteurs", max_length=500, blank=True)
    publisher = models.CharField("éditeur / organisme", max_length=255, blank=True)
    year = models.PositiveSmallIntegerField("année", null=True, blank=True)
    source_type = models.CharField("type", max_length=32, choices=SourceType.choices)
    identifier = models.CharField("identifiant (DOI, ISBN, n° d'analyse…)", max_length=255, blank=True)
    url = models.URLField("lien", max_length=500, blank=True)
    notes = models.TextField("notes", blank=True)
    is_demo = models.BooleanField(
        "donnée DEMO",
        default=False,
        db_index=True,
        help_text="Source fictive réservée aux démonstrations. Ne peut pas justifier une donnée validée.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "source documentaire"
        verbose_name_plural = "sources documentaires"
        ordering = ["title"]
        constraints = [
            models.CheckConstraint(
                condition=Q(year__isnull=True) | Q(year__gte=1800, year__lte=2100),
                name="sourcedocument_year_plausible",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.year})" if self.year else self.title


class ValidatedReferenceQuerySet(models.QuerySet):
    def validated(self):
        return self.filter(status=ValidationStatus.VALIDATED)

    def usable_for_engine(self):
        """Seules données autorisées pour un calcul réel : validées ET non DEMO."""
        return self.filter(status=ValidationStatus.VALIDATED, is_demo=False)

    def demo(self):
        return self.filter(is_demo=True)

    def awaiting_validation(self):
        return self.filter(status=ValidationStatus.PENDING)


def validated_reference_constraints():
    """Contraintes communes à toute donnée de référence (à inclure dans Meta.constraints)."""
    return [
        models.CheckConstraint(
            condition=~Q(is_demo=True, status=ValidationStatus.VALIDATED),
            name="%(app_label)s_%(class)s_demo_never_validated",
        ),
        models.CheckConstraint(
            condition=~Q(status=ValidationStatus.VALIDATED) | Q(validated_at__isnull=False),
            name="%(app_label)s_%(class)s_validated_has_date",
        ),
        models.CheckConstraint(
            condition=~Q(status=ValidationStatus.VALIDATED) | Q(source__isnull=False),
            name="%(app_label)s_%(class)s_validated_has_source",
        ),
    ]


class ValidatedReferenceModel(TimeStampedModel):
    source = models.ForeignKey(
        SourceDocument,
        verbose_name="source",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="%(class)s_items",
    )
    reference_date = models.DateField("date de référence", null=True, blank=True)
    status = models.CharField(
        "statut de validation",
        max_length=16,
        choices=ValidationStatus.choices,
        default=ValidationStatus.DRAFT,
        db_index=True,
    )
    is_demo = models.BooleanField(
        "donnée DEMO",
        default=False,
        db_index=True,
        help_text="Donnée fictive de démonstration : jamais utilisée pour une formulation réelle.",
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="validé par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    validated_at = models.DateTimeField("validé le", null=True, blank=True)
    validation_comment = models.TextField("commentaire de validation", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="créé par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    objects = ValidatedReferenceQuerySet.as_manager()

    class Meta:
        abstract = True

    @property
    def is_usable_for_engine(self) -> bool:
        return self.status == ValidationStatus.VALIDATED and not self.is_demo


class ValidationAction(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Soumis à validation"
    VALIDATED = "VALIDATED", "Validé"
    REJECTED = "REJECTED", "Rejeté"
    REVERTED = "REVERTED", "Remis en brouillon"


class ValidationRecord(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    action = models.CharField("action", max_length=16, choices=ValidationAction.choices)
    from_status = models.CharField("statut précédent", max_length=16, blank=True)
    to_status = models.CharField("nouveau statut", max_length=16)
    comment = models.TextField("commentaire", blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="auteur",
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    created_at = models.DateTimeField("date", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "décision de validation"
        verbose_name_plural = "historique des validations"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        return f"{self.get_action_display()} — {self.content_type.model} #{self.object_id}"


class ImportStatus(models.TextChoices):
    PENDING = "PENDING", "En attente"
    COMPLETED = "COMPLETED", "Terminé"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS", "Terminé avec erreurs"
    FAILED = "FAILED", "Échec"


class ImportBatch(models.Model):
    kind = models.CharField("type de données", max_length=64)
    file_name = models.CharField("fichier", max_length=255)
    file_sha256 = models.CharField("empreinte SHA-256", max_length=64, blank=True)
    status = models.CharField(max_length=24, choices=ImportStatus.choices, default=ImportStatus.PENDING)
    total_rows = models.PositiveIntegerField("lignes lues", default=0)
    created_rows = models.PositiveIntegerField("lignes créées", default=0)
    updated_rows = models.PositiveIntegerField("lignes mises à jour", default=0)
    error_rows = models.PositiveIntegerField("lignes en erreur", default=0)
    errors = models.JSONField("détail des erreurs", default=list, blank=True)
    is_demo = models.BooleanField("import DEMO", default=False)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "importation"
        verbose_name_plural = "historique des importations"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.kind} — {self.file_name}"


class ActivityLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="utilisateur",
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    farm = models.ForeignKey(
        "farms.Farm",
        verbose_name="exploitation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    action = models.CharField("action", max_length=64, db_index=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    object_repr = models.CharField("objet", max_length=255, blank=True)
    details = models.JSONField("détails", default=dict, blank=True)
    ip_address = models.GenericIPAddressField("adresse IP", null=True, blank=True)
    created_at = models.DateTimeField("date", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "activité"
        verbose_name_plural = "journal d'activité"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["farm", "-created_at"])]

    def __str__(self):
        return f"{self.action} — {self.object_repr}"
