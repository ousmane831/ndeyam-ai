"""Configuration des tests automatisés (pytest)."""

import tempfile
from pathlib import Path

from .base import *  # noqa: F401,F403

DEBUG = False
# Hachage rapide réservé aux tests (jamais utilisé hors tests).
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "anon": None,
        "user": None,
        "auth": "10000/minute",
        "assistant": "10000/minute",
    },
}
# Les tests ne doivent jamais appeler un fournisseur LLM réel.
LLM = {**LLM, "PROVIDER": "none", "API_KEY": ""}  # noqa: F405
EMBEDDINGS = {**EMBEDDINGS, "PROVIDER": "none", "API_KEY": ""}  # noqa: F405
# Aucun test n'écrit dans le vrai dossier media/ (les fichiers survivraient au retour arrière de la base).
MEDIA_ROOT = Path(tempfile.gettempdir()) / "ndeyam-ai-tests-media"
