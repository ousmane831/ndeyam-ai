"""Assistant vocal : nombres en lettres, détection de la demande, réponses calculées, service vocal."""

from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from voice import client
from voice.intents import detect, normalise, phrases
from voice.numbers import pulaar, spoken_amount, spoken_quantity, wolof

pytestmark = pytest.mark.django_db
WOLOF_UNITS = phrases()["wolof"]["units"]


@pytest.mark.parametrize(
    ("n", "words"),
    [
        (6, "juróom benn"),
        (30, "fanweer"),
        (42, "ñeent fukk ak ñaar"),
        (250, "ñaari téeméer ak juróom fukk"),
        (1056, "junni ak juróom fukk ak juróom benn"),
    ],
)
def test_wolof_numbers_are_spelled_out(n, words):
    assert wolof(n) == words


def test_pulaar_numbers_and_spoken_quantities():
    assert pulaar(42) == "capanɗe nayi e ɗiɗi"
    assert spoken_quantity(Decimal("0.92"), "wolof", WOLOF_UNITS) == "juróom ñeenti téeméer gramme"
    assert spoken_quantity(Decimal("5.52"), "wolof", WOLOF_UNITS) == "juróom kilo ak genn-wàll"
    assert (
        spoken_amount(Decimal("1056.4"), "wolof", WOLOF_UNITS) == "junni ak juróom fukk ak juróom benn franc"
    )
    # Aucun chiffre dans le texte parlé : la synthèse vocale ne sait pas les lire.
    assert not any(c.isdigit() for c in spoken_quantity(Decimal("8.4"), "wolof", WOLOF_UNITS))


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("attaque fra kilo fra laa wara jox sama xar yi bés bu nekk", "ration"),  # transcription réelle
        ("Ñaata kilo la sama xar yi diis ?", "weighing"),  # « kilo » n'en fait pas une question de ration
        ("ñaata xaalis laa dépenser ci lekk", "cost"),
        ("Lan laa wara def tey ?", "tasks"),
        # « tey » (aujourd'hui) n'est qu'un mot de temps : il ne fait pas d'une question de ration une tâche.
        ("Lan laa wara jox sama xar yi tey ?", "ration"),
        ("Ñaata la sama xar yi diis tey ?", "weighing"),
        ("sama xar yi dañuy yokk", "growth"),
        ("bonjour", "unknown"),
    ],
)
def test_wolof_requests_are_recognised(text, intent):
    assert detect(text, "wolof")[0] == intent


def test_detection_ignores_accents_and_spelling_variants():
    assert normalise("Ñaata BÉS bu nëkk ?") == "naata bes bu nekk"
    assert detect("o fotii kilo mi hokkata baay li am ñalnde kala", "pulaar")[0] == "ration"
    assert detect("ko mi hokkata baali am hannde", "pulaar")[0] == "ration"  # « hannde » : aujourd'hui


@pytest.fixture
def voice_on(settings, monkeypatch):
    settings.VOICE_SERVICE = {"URL": "https://voix.example", "API_KEY": "", "TIMEOUT": 5}
    calls = {}

    def fake_transcribe(audio, filename, content_type, language):
        calls["transcribe"] = (len(audio), language)
        return "Ñaata kilo laa wara jox sama xar yi bés bu nekk"

    def fake_synthesize(text, language):
        calls["synthesize"] = (text, language)
        return "https://voix.example/audio/reponse.wav"

    monkeypatch.setattr(client, "transcribe", fake_transcribe)
    monkeypatch.setattr(client, "synthesize", fake_synthesize)
    return calls


def test_spoken_question_gets_a_spoken_answer_from_farm_data(api, breeder, client_for, farm, voice_on):
    audio = (Path(__file__).parent / "question_wolof.wav").read_bytes()
    response = client_for(breeder).post(
        "/api/v1/voice/ask/",
        {"audio": SimpleUploadedFile("q.wav", audio, "audio/wav"), "language": "wo", "farm": farm.pk},
        format="multipart",
    )
    body = response.json()
    assert response.status_code == 200, body
    assert body["intent"] == "ration" and body["language"] == "wolof"
    assert body["segments"][0]["audio_url"] == "https://voix.example/audio/reponse.wav"
    assert voice_on["transcribe"] == (len(audio), "wolof")  # code court « wo » converti
    assert voice_on["synthesize"][0] in body["spoken_text"]
    assert "Aucune ration en cours" in body["text"]  # aucune ration : rien n'est inventé


def test_touch_question_uses_real_numbers_written_in_words(api, breeder, client_for, farm, animal, voice_on):
    from feeding.models import FeedingRecord

    FeedingRecord.objects.create(
        farm=farm, animal=animal, quantity_distributed_kg=Decimal("2"), estimated_cost=Decimal("1056")
    )
    response = client_for(breeder).post(
        "/api/v1/voice/answer/", {"intent": "cost", "language": "wolof"}, format="json"
    )
    body = response.json()
    assert response.status_code == 200, body
    assert "1 056 FCFA" in body["text"]
    assert "junni ak juróom fukk ak juróom benn franc" in body["spoken_text"]


def test_serere_is_heard_but_answered_in_wolof(api, breeder, client_for, farm, voice_on):
    audio = SimpleUploadedFile("q.wav", b"RIFF0000", "audio/wav")
    response = client_for(breeder).post(
        "/api/v1/voice/ask/", {"audio": audio, "language": "serere"}, format="multipart"
    )
    assert response.status_code == 200 and response.json()["language"] == "wolof"
    assert voice_on["transcribe"][1] == "serere"


def test_voice_is_off_without_a_service_and_isolated_by_farm(
    api, breeder, client_for, farm, settings, make_farm, make_user
):
    settings.VOICE_SERVICE = {"URL": "", "API_KEY": "", "TIMEOUT": 5}
    c = client_for(breeder)
    assert c.get("/api/v1/voice/status/").json()["configured"] is False
    assert (
        c.post("/api/v1/voice/answer/", {"intent": "ration", "language": "wolof"}, format="json").status_code
        == 503
    )
    settings.VOICE_SERVICE = {"URL": "https://voix.example", "API_KEY": "", "TIMEOUT": 5}
    other = make_farm(owner=make_user())
    stranger = c.post(
        "/api/v1/voice/answer/", {"intent": "ration", "language": "wolof", "farm": other.pk}, format="json"
    )
    assert stranger.status_code == 404  # l'exploitation d'un autre éleveur n'existe pas pour lui
    unsupported = c.post("/api/v1/voice/answer/", {"intent": "ration", "language": "fr"}, format="json")
    assert unsupported.status_code == 400


def test_service_errors_are_explained(api, breeder, client_for, farm, settings, monkeypatch):
    settings.VOICE_SERVICE = {"URL": "https://voix.example", "API_KEY": "", "TIMEOUT": 5}

    def down(*args, **kwargs):
        raise client.VoiceServiceError("Le service vocal ne répond pas. Réessayez dans un instant.", 503)

    monkeypatch.setattr(client, "transcribe", down)
    audio = SimpleUploadedFile("q.wav", b"RIFF0000", "audio/wav")
    response = client_for(breeder).post(
        "/api/v1/voice/ask/", {"audio": audio, "language": "wolof"}, format="multipart"
    )
    assert response.status_code == 503 and "ne répond pas" in response.json()["detail"]
