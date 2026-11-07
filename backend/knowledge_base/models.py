"""
Base documentaire (RAG).

Les embeddings sont stockés dans un tableau PostgreSQL (`real[]`) et la similarité est calculée
en Python (NumPy) derrière une interface VectorStore. Une colonne pgvector pourra être ajoutée
ultérieurement et remplie à partir de ces mêmes valeurs, sans réindexer les documents.
Seuls les documents VALIDÉS sont interrogés par l'assistant.
"""

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models import F, Q

from governance.models import ValidatedReferenceModel, validated_reference_constraints


class ProcessingStatus(models.TextChoices):
    UPLOADED = "UPLOADED", "Importé"
    PROCESSING = "PROCESSING", "En cours de traitement"
    INDEXED = "INDEXED", "Indexé"
    FAILED = "FAILED", "Échec du traitement"


class TechnicalDocument(ValidatedReferenceModel):
    title = models.CharField("titre", max_length=300)
    description = models.TextField("description", blank=True)
    file = models.FileField("fichier", upload_to="documents/%Y/%m/")
    file_sha256 = models.CharField("empreinte SHA-256", max_length=64, unique=True)
    mime_type = models.CharField("type de fichier", max_length=100, default="application/pdf")
    size_bytes = models.PositiveBigIntegerField("taille (octets)", default=0)
    page_count = models.PositiveIntegerField("nombre de pages", null=True, blank=True)
    language = models.CharField("langue", max_length=8, default="fr")
    processing_status = models.CharField(
        "traitement", max_length=16, choices=ProcessingStatus.choices, default=ProcessingStatus.UPLOADED
    )
    processing_error = models.TextField("erreur de traitement", blank=True)
    indexed_at = models.DateTimeField("indexé le", null=True, blank=True)
    embedding_model = models.CharField("modèle d'embeddings", max_length=150, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        verbose_name = "document technique"
        verbose_name_plural = "documents techniques"
        ordering = ["-created_at"]
        constraints = [*validated_reference_constraints()]

    def __str__(self):
        return self.title

    def extra_validation_blockers(self):
        """Un document ne peut être validé que s'il a été indexé avec succès."""
        if self.processing_status != ProcessingStatus.INDEXED:
            return ["Le document doit être indexé avec succès avant d'être validé."]
        return []


class DocumentChunk(models.Model):
    document = models.ForeignKey(TechnicalDocument, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField("rang")
    text = models.TextField("texte")
    page_start = models.PositiveIntegerField("page de début", null=True, blank=True)
    page_end = models.PositiveIntegerField("page de fin", null=True, blank=True)
    char_count = models.PositiveIntegerField("caractères", default=0)
    embedding = ArrayField(models.FloatField(), null=True, blank=True)
    embedding_model = models.CharField(max_length=150, blank=True)
    search_vector = SearchVectorField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "passage"
        verbose_name_plural = "passages"
        ordering = ["document", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"], name="chunk_unique_index_per_document"
            ),
            models.CheckConstraint(
                condition=Q(page_start__isnull=True)
                | Q(page_end__isnull=True)
                | Q(page_start__lte=F("page_end")),
                name="chunk_pages_ordered",
            ),
        ]
        indexes = [GinIndex(fields=["search_vector"], name="chunk_search_vector_gin")]

    def __str__(self):
        return f"{self.document} — passage {self.chunk_index}"
