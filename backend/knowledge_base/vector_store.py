"""
Stockage vectoriel derrière une interface unique (VECTOR_STORE_BACKEND).

- numpy (défaut) : embeddings stockés en `real[]` dans DocumentChunk, similarité cosinus calculée en mémoire.
  Adapté à quelques dizaines de milliers de passages.
- pgvector : prévu. Il suffira d'ajouter une colonne `vector`, de la remplir à partir de `embedding` (sans
  réindexer les documents) et d'implémenter `search` avec l'opérateur `<=>`.
"""

import numpy as np
from django.conf import settings


class VectorStoreError(RuntimeError):
    pass


class NumpyVectorStore:
    name = "numpy"

    def search(self, query_vector, chunks_queryset, model_id, k=5):
        rows = list(
            chunks_queryset.filter(embedding__isnull=False, embedding_model=model_id).values_list(
                "id", "embedding"
            )
        )
        if not rows:
            return []
        ids = [r[0] for r in rows]
        matrix = np.asarray([r[1] for r in rows], dtype=np.float32)
        query = np.asarray(query_vector, dtype=np.float32)
        if matrix.shape[1] != query.shape[0]:
            raise VectorStoreError(
                "Dimensions d'embedding incompatibles : réindexez les documents avec le modèle actuel."
            )
        norms = np.linalg.norm(matrix, axis=1) * (np.linalg.norm(query) or 1.0)
        norms[norms == 0] = 1.0
        scores = matrix @ query / norms
        order = np.argsort(-scores)[:k]
        return [(ids[i], float(scores[i])) for i in order]


class PgVectorStore:
    name = "pgvector"

    def search(self, *args, **kwargs):
        raise VectorStoreError(
            "Le stockage pgvector n'est pas encore activé dans cette version : "
            "utilisez VECTOR_STORE_BACKEND=numpy."
        )


def get_vector_store():
    backend = settings.VECTOR_STORE_BACKEND
    if backend == "pgvector":
        return PgVectorStore()
    return NumpyVectorStore()
