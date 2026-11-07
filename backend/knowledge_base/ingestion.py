"""
Ingestion d'un document technique : PDF → texte → passages → index plein texte → embeddings (si configurés).

Le traitement est synchrone (documents de taille raisonnable). Un échec est enregistré sur le document
(statut « Échec » et message) au lieu de produire un index partiel silencieux.
"""

import hashlib
import logging

from django.db import connection, transaction
from django.utils import timezone

from governance.activity import log_activity

from .embeddings import EmbeddingError, get_embedding_provider
from .models import DocumentChunk, ProcessingStatus, TechnicalDocument
from .pdf import PdfExtractionError, extract_pages
from .text import chunk_pages, strip_accents

logger = logging.getLogger(__name__)
MAX_FILE_BYTES = 20 * 1024 * 1024


class DuplicateDocumentError(ValueError):
    def __init__(self, existing):
        super().__init__(f"Ce fichier a déjà été importé (« {existing.title} »).")
        self.existing = existing


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _index_full_text(document):
    """Vecteur plein texte français calculé sur le texte SANS accents (requêtes tapées sans accents)."""
    with connection.cursor() as cursor:
        for chunk_id, text in document.chunks.values_list("id", "text"):
            cursor.execute(
                "UPDATE knowledge_base_documentchunk "
                "SET search_vector = to_tsvector('french', %s) WHERE id = %s",
                [strip_accents(f"{document.title}\n{text}"), chunk_id],
            )


def _embed(document, provider):
    chunks = list(document.chunks.order_by("chunk_index"))
    vectors = provider.embed([c.text for c in chunks])
    for chunk, vector in zip(chunks, vectors, strict=True):
        chunk.embedding = [float(x) for x in vector]
        chunk.embedding_model = provider.model_id
    DocumentChunk.objects.bulk_update(chunks, ["embedding", "embedding_model"])
    document.embedding_model = provider.model_id


def process_document(document, data: bytes, provider="auto"):
    """(Ré)indexe le document. Retourne la liste des avertissements."""
    warnings = []
    document.processing_status = ProcessingStatus.PROCESSING
    document.processing_error = ""
    document.save(update_fields=["processing_status", "processing_error", "updated_at"])
    try:
        pages = extract_pages(data)
        chunks = chunk_pages(pages)
        with transaction.atomic():
            document.chunks.all().delete()
            DocumentChunk.objects.bulk_create(
                [
                    DocumentChunk(
                        document=document,
                        chunk_index=c.index,
                        text=c.text,
                        page_start=c.page_start,
                        page_end=c.page_end,
                        char_count=len(c.text),
                    )
                    for c in chunks
                ]
            )
            document.page_count = len(pages)
            _index_full_text(document)
    except PdfExtractionError as exc:
        document.processing_status = ProcessingStatus.FAILED
        document.processing_error = str(exc)
        document.save(update_fields=["processing_status", "processing_error", "updated_at"])
        return [str(exc)]

    provider = get_embedding_provider() if provider == "auto" else provider
    document.embedding_model = ""
    if provider is None:
        warnings.append(
            "Aucun fournisseur d'embeddings configuré : le document est indexé en plein texte uniquement."
        )
    else:
        try:
            _embed(document, provider)
        except EmbeddingError as exc:
            logger.warning("Embeddings indisponibles pour le document %s : %s", document.pk, exc)
            warnings.append(
                f"Embeddings non calculés ({exc}) : recherche plein texte uniquement pour ce document."
            )
    document.processing_status = ProcessingStatus.INDEXED
    document.indexed_at = timezone.now()
    document.save(
        update_fields=["processing_status", "page_count", "indexed_at", "embedding_model", "updated_at"]
    )
    return warnings


def import_document(
    *,
    upload,
    title,
    user,
    request=None,
    description="",
    source=None,
    language="fr",
    is_demo=False,
    reference_date=None,
):
    data = upload.read()
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("Fichier trop volumineux (20 Mo maximum).")
    if not data.startswith(b"%PDF"):
        raise ValueError("Seuls les fichiers PDF sont acceptés.")
    digest = sha256_of(data)
    existing = TechnicalDocument.objects.filter(file_sha256=digest).first()
    if existing:
        raise DuplicateDocumentError(existing)
    upload.seek(0)
    document = TechnicalDocument(
        title=title,
        description=description,
        source=source,
        language=language,
        is_demo=is_demo,
        reference_date=reference_date,
        file_sha256=digest,
        size_bytes=len(data),
        mime_type="application/pdf",
        uploaded_by=user,
        created_by=user,
    )
    document.file.save(getattr(upload, "name", "document.pdf"), upload, save=False)
    document.save()
    warnings = process_document(document, data)
    log_activity(
        request,
        "document.imported",
        document,
        actor=user,
        details={"pages": document.page_count, "status": document.processing_status},
    )
    return document, warnings


def reindex_document(document, request=None):
    with document.file.open("rb") as handle:
        data = handle.read()
    warnings = process_document(document, data)
    log_activity(request, "document.reindexed", document, details={"status": document.processing_status})
    return warnings
