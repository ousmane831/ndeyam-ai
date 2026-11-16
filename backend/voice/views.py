"""
Assistant vocal : l'éleveur parle (wolof, pulaar, sérère) ou touche une question illustrée, Ndeyam calcule la
réponse sur ses données, et la lit à voix haute (wolof, pulaar).
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from farms.access import readable_farms
from governance.activity import log_activity

from . import client
from .answers import LABELS, build_answer
from .intents import INTENTS, detect

MAX_AUDIO_BYTES = 8 * 1024 * 1024  # environ 2 minutes de parole en WAV 16 kHz


class _Throttled(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "assistant"

    def get_throttles(self):
        from rest_framework.throttling import ScopedRateThrottle

        return [ScopedRateThrottle()]


def _farm(user, farm_id):
    farms = readable_farms(user).filter(is_active=True)
    if str(farm_id or "").isdigit():
        return farms.filter(pk=farm_id).first()
    return (
        farms.order_by("-is_demo", "name").first()
        if user.is_platform_admin
        else farms.order_by("name").first()
    )


def _speak(sentences, language):
    """Chaque phrase lue séparément (phrases courtes : mieux comprises) ; appels en parallèle."""
    from concurrent.futures import ThreadPoolExecutor

    def one(text):
        try:
            return {"text": text, "audio_url": client.synthesize(text, language), "error": None}
        except client.VoiceServiceError as exc:
            return {"text": text, "audio_url": None, "error": exc.message}

    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(one, sentences))


def _answer(request, *, intent, language, farm, transcript=None, keywords=()):
    sentences, shown, data = build_answer(intent, farm, language)
    segments = _speak(sentences, language) if language in client.TTS_LANGUAGES else []
    log_activity(request, "voice.answered", farm=farm, details={"intent": intent, "language": language})
    errors = [s["error"] for s in segments if s["error"]]
    return Response(
        {
            "language": language,
            "transcript": transcript,
            "intent": intent,
            "intent_label": LABELS[intent],
            "keywords": list(keywords),
            "spoken_text": " ".join(sentences),
            "segments": segments,
            "audio_error": errors[0] if errors else None,
            "text": shown,
            "farm": {"id": farm.pk, "name": farm.name, "is_demo": farm.is_demo},
            "data": data,
        }
    )


class VoiceStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=OpenApiTypes.OBJECT, summary="Assistant vocal : disponibilité, langues, questions"
    )
    def get(self, request):
        return Response(
            {
                "configured": client.is_configured(),
                "speech_languages": list(client.ASR_LANGUAGES),
                "voice_languages": list(client.TTS_LANGUAGES),
                "intents": [{"code": code, "label": LABELS[code]} for code in INTENTS],
            }
        )


class VoiceAskSerializer(serializers.Serializer):
    audio = serializers.FileField()
    language = serializers.CharField()
    farm = serializers.IntegerField(required=False)


class VoiceAnswerSerializer(serializers.Serializer):
    intent = serializers.ChoiceField(choices=list(INTENTS))
    language = serializers.CharField()
    farm = serializers.IntegerField(required=False)


def _language(value, allowed):
    lang = client.normalise_language(value)
    if lang not in allowed:
        raise serializers.ValidationError({"language": f"Langue non prise en charge : {value}."})
    return lang


class VoiceAskView(_Throttled):
    """Question parlée : voix → texte (service vocal) → demande reconnue → réponse calculée → voix."""

    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request=VoiceAskSerializer, responses=OpenApiTypes.OBJECT, summary="Poser une question à voix haute"
    )
    def post(self, request):
        if not client.is_configured():
            return Response(
                {"detail": "L'assistant vocal n'est pas activé.", "code": "voice_disabled"}, status=503
            )
        payload = VoiceAskSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        audio = payload.validated_data["audio"]
        language = _language(payload.validated_data["language"], client.ASR_LANGUAGES)
        if audio.size > MAX_AUDIO_BYTES:
            return Response(
                {"detail": "Enregistrement trop long (2 minutes au plus).", "code": "too_large"}, status=400
            )
        farm = _farm(request.user, payload.validated_data.get("farm"))
        if farm is None:
            return Response({"detail": "Aucune exploitation accessible.", "code": "no_farm"}, status=404)
        try:
            transcript = client.transcribe(audio.read(), audio.name, audio.content_type, language)
        except client.VoiceServiceError as exc:
            return Response({"detail": exc.message, "code": "voice_service"}, status=exc.status)
        intent, keywords = detect(transcript, language)
        # Réponse parlée : dans la langue de la question si la synthèse la connaît, sinon en wolof.
        spoken_language = language if language in client.TTS_LANGUAGES else "wolof"
        return _answer(
            request,
            intent=intent,
            language=spoken_language,
            farm=farm,
            transcript=transcript,
            keywords=keywords,
        )


class VoiceAnswerView(_Throttled):
    """Question choisie d'un toucher (sans parler) : réponse calculée et lue à voix haute."""

    parser_classes = [JSONParser, FormParser]

    @extend_schema(
        request=VoiceAnswerSerializer, responses=OpenApiTypes.OBJECT, summary="Réponse parlée à une question"
    )
    def post(self, request):
        if not client.is_configured():
            return Response(
                {"detail": "L'assistant vocal n'est pas activé.", "code": "voice_disabled"}, status=503
            )
        payload = VoiceAnswerSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        language = _language(payload.validated_data["language"], client.TTS_LANGUAGES)
        farm = _farm(request.user, payload.validated_data.get("farm"))
        if farm is None:
            return Response({"detail": "Aucune exploitation accessible.", "code": "no_farm"}, status=404)
        return _answer(request, intent=payload.validated_data["intent"], language=language, farm=farm)
