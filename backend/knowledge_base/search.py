"""
Recherche documentaire (utilisée par l'écran de recherche et, à l'étape 10, par l'assistant).

1. Si un fournisseur d'embeddings est configuré et que des passages ont été vectorisés avec le même modèle :
   recherche SÉMANTIQUE (similarité cosinus) ;
2. sinon, ou si la recherche sémantique échoue : recherche PLEIN TEXTE PostgreSQL
   (français, insensible aux accents).

Par défaut, seuls les documents VALIDÉS et non DEMO sont interrogés.
Chaque résultat porte la référence complète : titre, pages, source.
"""

import logging

from django.contrib.postgres.search import SearchQuery, SearchRank

from governance.models import ValidationStatus

from .embeddings import EmbeddingError, get_embedding_provider
from .models import DocumentChunk, ProcessingStatus, TechnicalDocument
from .text import strip_accents
from .vector_store import VectorStoreError, get_vector_store

logger = logging.getLogger(__name__)
EXCERPT = 600


def searchable_documents(include_unvalidated=False):
    qs = TechnicalDocument.objects.filter(processing_status=ProcessingStatus.INDEXED)
    if include_unvalidated:
        return qs.exclude(status=ValidationStatus.REJECTED)
    return qs.usable_for_engine()


def _result(chunk, score, method):
    doc = chunk.document
    pages = (
        f"p. {chunk.page_start}"
        if chunk.page_start == chunk.page_end
        else f"p. {chunk.page_start}-{chunk.page_end}"
    )
    text = chunk.text if len(chunk.text) <= EXCERPT else chunk.text[:EXCERPT].rsplit(" ", 1)[0] + " …"
    return {
        "chunk_id": chunk.pk,
        "document_id": doc.pk,
        "document_title": doc.title,
        "pages": pages,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "source": str(doc.source) if doc.source_id else None,
        "document_status": doc.status,
        "is_demo": doc.is_demo,
        "excerpt": text,
        "score": round(score, 4),
        "method": method,
        "citation": f"{doc.title}, {pages}" + (f" — {doc.source}" if doc.source_id else ""),
    }


def search(query, k=5, include_unvalidated=False, provider="auto"):
    query = (query or "").strip()
    if not query:
        return {"results": [], "method": None, "warnings": ["Saisissez une question ou des mots-clés."]}
    chunks = DocumentChunk.objects.filter(
        document__in=searchable_documents(include_unvalidated)
    ).select_related("document__source")
    warnings = []
    provider = get_embedding_provider() if provider == "auto" else provider
    if provider is not None:
        try:
            vector = provider.embed([query])[0]
            hits = get_vector_store().search(vector, chunks, provider.model_id, k=k)
            if hits:
                by_id = chunks.in_bulk([h[0] for h in hits])
                return {
                    "results": [_result(by_id[i], s, "semantique") for i, s in hits],
                    "method": "semantique",
                    "warnings": warnings,
                }
            warnings.append("Aucun passage vectorisé avec le modèle actuel : recherche plein texte.")
        except (EmbeddingError, VectorStoreError) as exc:
            logger.warning("Recherche sémantique indisponible : %s", exc)
            warnings.append(f"Recherche sémantique indisponible ({exc}) : recherche plein texte.")

    ts_query = SearchQuery(strip_accents(query), config="french", search_type="websearch")
    ranked = (
        chunks.filter(search_vector=ts_query)
        .annotate(rank=SearchRank("search_vector", ts_query))
        .order_by("-rank")[:k]
    )
    results = [_result(c, c.rank, "plein_texte") for c in ranked]
    if not results:
        warnings.append("Aucun passage ne correspond dans les documents disponibles.")
    return {"results": results, "method": "plein_texte", "warnings": warnings}
