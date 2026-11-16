"""
Appel HTTP POST avec nouvelles tentatives, pour les fournisseurs d'IA (LLM, embeddings).

Les offres gratuites (Gemini, Groq…) refusent souvent une requête isolée : quota par minute dépassé (429),
modèle surchargé (500, 502, 503, 504), voire refus d'autorisation passager (403, observé sur des clés
Gemini fraîchement créées). On réessaie deux fois après une courte pause avant de remonter l'erreur.
Une clé réellement invalide (401, 403 persistant) échoue donc au bout de quelques secondes seulement.
Les erreurs réseau et délais dépassés ne sont pas réessayés (le délai est déjà long).
"""

import logging
import time

logger = logging.getLogger(__name__)

RETRY_STATUSES = frozenset({403, 429, 500, 502, 503, 504})
RETRY_DELAYS = (1.5, 3.0)  # secondes ; mis à zéro dans les tests (conftest.py)
MAX_RETRY_AFTER = 10.0


def _delay(response, default):
    """Respecte l'en-tête Retry-After s'il est court, sinon la pause par défaut."""
    try:
        return min(max(float(response.headers.get("retry-after", "")), default), MAX_RETRY_AFTER)
    except ValueError:
        return default


def post_with_retry(client, url, **kwargs):
    """`client.post(url, **kwargs)`, réessayé sur les statuts passagers. Renvoie la dernière réponse."""
    response = client.post(url, **kwargs)
    for default in RETRY_DELAYS:
        if response.status_code not in RETRY_STATUSES:
            break
        pause = _delay(response, default) if default else 0
        logger.info("Fournisseur d'IA : statut %s, nouvel essai dans %.1f s.", response.status_code, pause)
        time.sleep(pause)
        response = client.post(url, **kwargs)
    return response
