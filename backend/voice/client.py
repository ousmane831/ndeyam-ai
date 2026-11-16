"""
Client du service vocal (Sama Agri Voice) : reconnaissance (voix → texte) et synthèse (texte → voix).

Seules ces deux briques sont utilisées : le raisonnement et les chiffres viennent de Ndeyam (données de
l'exploitation, moteur de formulation), jamais d'un modèle qui pourrait inventer une ration.
Adresse : VOICE_SERVICE_URL ; clé facultative : VOICE_SERVICE_API_KEY (en-tête « Authorization: Bearer »).
"""

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid

from django.conf import settings

# Langues du service : la reconnaissance accepte le sérère, la synthèse seulement le wolof et le pulaar.
ASR_LANGUAGES = ("wolof", "pulaar", "serere")
TTS_LANGUAGES = ("wolof", "pulaar")
SHORT_CODES = {"wo": "wolof", "ff": "pulaar", "fuc": "pulaar", "sr": "serere", "srr": "serere"}


class VoiceServiceError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.message = message
        self.status = status


def normalise_language(value):
    lang = (value or "").strip().lower()
    return SHORT_CODES.get(lang, lang)


def is_configured():
    return bool(settings.VOICE_SERVICE["URL"])


def _base():
    url = settings.VOICE_SERVICE["URL"].rstrip("/")
    if not url.startswith(("https://", "http://")):
        raise VoiceServiceError("Adresse du service vocal invalide (http ou https attendu).", 503)
    return url


def _headers(extra=None):
    headers = dict(extra or {})
    if settings.VOICE_SERVICE["API_KEY"]:
        headers["Authorization"] = f"Bearer {settings.VOICE_SERVICE['API_KEY']}"
    return headers


def _call(request):
    try:
        with urllib.request.urlopen(request, timeout=settings.VOICE_SERVICE["TIMEOUT"]) as response:  # noqa: S310 (http(s) vérifié)
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise VoiceServiceError(f"Le service vocal a refusé la demande (code {exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise VoiceServiceError("Le service vocal ne répond pas. Réessayez dans un instant.", 503) from exc
    except ValueError as exc:
        raise VoiceServiceError("Réponse illisible du service vocal.") from exc


def transcribe(audio: bytes, filename: str, content_type: str, language: str) -> str:
    """Voix → texte dans la langue parlée (jamais traduit)."""
    boundary = uuid.uuid4().hex
    safe_name = filename.replace('"', "") or "question.wav"
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="language"\r\n\r\n{language}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="audio"; filename="{safe_name}"\r\n'
            f"Content-Type: {content_type or 'application/octet-stream'}\r\n\r\n"
        ).encode()
        + audio
        + f"\r\n--{boundary}--\r\n".encode()
    )
    request = urllib.request.Request(  # noqa: S310 (adresse http(s) vérifiée par _base)
        f"{_base()}/api/v1/agriculture/transcribe",
        data=body,
        headers=_headers({"Content-Type": f"multipart/form-data; boundary={boundary}"}),
    )
    return (_call(request).get("question") or "").strip()


def synthesize(text: str, language: str) -> str:
    """Texte → voix ; renvoie l'adresse complète du fichier audio (WAV)."""
    data = urllib.parse.urlencode({"text": text, "language": language}).encode("utf-8")
    request = urllib.request.Request(  # noqa: S310 (adresse http(s) vérifiée par _base)
        f"{_base()}/api/v1/agriculture/synthesize",
        data=data,
        headers=_headers({"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}),
    )
    url = _call(request).get("audio_url") or ""
    return url if url.startswith("http") else f"{_base()}{url}"
