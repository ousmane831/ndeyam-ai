"""
Fournisseurs d'embeddings (indépendants du fournisseur, configurés dans `.env`).

EMBEDDING_PROVIDER :
- none              : aucun embedding ; la recherche utilise le plein texte PostgreSQL ;
- openai_compatible : POST {EMBEDDING_BASE_URL}/embeddings  {model, input: [...]}
                      (OpenAI, Mistral, LM Studio…) ;
- ollama            : POST {EMBEDDING_BASE_URL}/api/embed   {model, input: [...]}  (modèle local).

Aucune clé n'est journalisée ni renvoyée par l'API.
"""

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)
BATCH_SIZE = 64


class EmbeddingError(RuntimeError):
    pass


class EmbeddingProvider:
    name = "none"

    def __init__(self, model="", api_key="", base_url="", client=None, timeout=60):
        self.model = model
        self.api_key = api_key
        self.base_url = (base_url or "").rstrip("/")
        self.client = client or httpx.Client(timeout=timeout)

    @property
    def model_id(self) -> str:
        return f"{self.name}:{self.model}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for start in range(0, len(texts), BATCH_SIZE):
            vectors.extend(self._embed_batch(texts[start : start + BATCH_SIZE]))
        if len(vectors) != len(texts):
            raise EmbeddingError("Le fournisseur n'a pas renvoyé un vecteur par passage.")
        return vectors

    def _post(self, url, payload, headers=None):
        try:
            response = self.client.post(url, json=payload, headers=headers or {})
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"Fournisseur d'embeddings injoignable ({exc.__class__.__name__}).") from exc
        if response.status_code >= 400:
            raise EmbeddingError(f"Le fournisseur d'embeddings a répondu {response.status_code}.")
        return response.json()

    def _embed_batch(self, texts):  # pragma: no cover - surchargé
        raise NotImplementedError


class OpenAICompatibleEmbeddings(EmbeddingProvider):
    name = "openai_compatible"

    def _embed_batch(self, texts):
        data = self._post(
            f"{self.base_url}/embeddings",
            {"model": self.model, "input": texts},
            {"Authorization": f"Bearer {self.api_key}"},
        )
        items = sorted(data.get("data", []), key=lambda item: item.get("index", 0))
        return [item["embedding"] for item in items]


class OllamaEmbeddings(EmbeddingProvider):
    name = "ollama"

    def _embed_batch(self, texts):
        data = self._post(f"{self.base_url}/api/embed", {"model": self.model, "input": texts})
        return data.get("embeddings", [])


PROVIDERS = {"openai_compatible": OpenAICompatibleEmbeddings, "ollama": OllamaEmbeddings}


def configuration_problem(config=None) -> str | None:
    config = config or settings.EMBEDDINGS
    provider = config["PROVIDER"]
    if provider in ("", "none"):
        return "Aucun fournisseur d'embeddings configuré : recherche plein texte uniquement."
    if provider not in PROVIDERS:
        return f"Fournisseur d'embeddings inconnu : « {provider} »."
    if not config["MODEL"] or not config["BASE_URL"]:
        return "EMBEDDING_MODEL et EMBEDDING_BASE_URL doivent être renseignés."
    if provider == "openai_compatible" and not config["API_KEY"]:
        return "EMBEDDING_API_KEY doit être renseignée pour ce fournisseur."
    return None


def get_embedding_provider(client=None) -> EmbeddingProvider | None:
    """Fournisseur configuré, ou None (la recherche se replie alors sur le plein texte)."""
    config = settings.EMBEDDINGS
    if configuration_problem(config):
        return None
    return PROVIDERS[config["PROVIDER"]](
        model=config["MODEL"], api_key=config["API_KEY"], base_url=config["BASE_URL"], client=client
    )
