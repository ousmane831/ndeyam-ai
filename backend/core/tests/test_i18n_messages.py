"""Messages du serveur en anglais à la demande (Accept-Language), sans jamais toucher aux données saisies."""

import pytest

from core import i18n_messages
from core.i18n_messages import translate_text, translate_tree

pytestmark = pytest.mark.django_db


def test_exact_and_pattern_messages_are_translated():
    assert translate_text("Les données envoyées sont invalides.") == "The data sent is invalid."
    assert (
        translate_text("Suppression impossible : cet élément est encore utilisé (animaux, pesées).")
        == "Cannot delete: this item is still in use (animals, weighings)."
    )


def test_unknown_text_and_user_data_are_left_untouched():
    assert translate_text("Bélier de Fatou, très calme") == "Bélier de Fatou, très calme"
    data = {"name": "Les données envoyées sont invalides.", "detail": "Les données envoyées sont invalides."}
    assert translate_tree(data) == {
        "name": "Les données envoyées sont invalides.",
        "detail": "The data sent is invalid.",
    }


def test_captured_parts_are_translated_piece_by_piece(monkeypatch):
    exact = {
        "teneur en matière sèche inconnue": "dry matter content unknown",
        "prix inconnu": "price unknown",
    }
    patterns = [(r"« (?P<name>.+) » exclu : (?P<why>.+)\.", "“{name}” excluded: {why}.")]
    import re

    monkeypatch.setattr(
        i18n_messages, "_catalog", lambda: (exact, [(re.compile(p + r"\Z"), t) for p, t in patterns])
    )
    assert (
        translate_text("« [DEMO] Son » exclu : teneur en matière sèche inconnue ; prix inconnu.")
        == "“[DEMO] Son” excluded: dry matter content unknown ; price unknown."
    )


def test_api_answers_in_english_only_when_asked(api, breeder, client_for):
    client = client_for(breeder)
    fr = client.post("/api/v1/animals/", {}, format="json")
    en = client.post("/api/v1/animals/", {}, format="json", HTTP_ACCEPT_LANGUAGE="en")
    assert fr.json()["detail"] == "Les données envoyées sont invalides."
    assert en.json()["detail"] == "The data sent is invalid."
    # Messages natifs de Django REST framework : traduits par Django lui-même.
    assert any("required" in m for msgs in en.json()["errors"].values() for m in msgs)
