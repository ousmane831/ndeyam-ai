"""
Détection de la demande dans la phrase transcrite, par mots-clés (phrases.json, relu par des locuteurs).

La transcription garde la langue parlée, avec des emprunts au français et une orthographe variable (« jaay »,
« jaye ») : on compare donc des textes sans accents ni majuscules. Ordre de priorité en cas d'égalité : une
question de poids ou d'argent contient souvent « kilo », qui ne doit pas faire croire à une question de
ration.
"""

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

INTENTS = ("weighing", "cost", "growth", "tasks", "ration")
PRIORITY = {name: rank for rank, name in enumerate(INTENTS)}


@lru_cache(maxsize=1)
def phrases():
    return json.loads((Path(__file__).parent / "phrases.json").read_text(encoding="utf-8"))


def normalise(text):
    """Minuscules, sans accents (ñ → n, ë → e), ponctuation retirée, espaces simples."""
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9' ]+", " ", plain).split())


def detect(text, language):
    """Renvoie (intention, mots-clés trouvés) ; intention « unknown » si rien ne correspond."""
    padded = f" {normalise(text)} "
    keywords = phrases().get(language, {}).get("keywords", {})
    best, best_hits = "unknown", []
    for intent in INTENTS:
        hits = []
        for keyword in keywords.get(intent, []):
            k = normalise(keyword)
            # Début de mot : « jox » trouve « joxal », « natt » trouve « nattal », jamais au milieu d'un mot.
            if k and re.search(rf"(?<![a-z0-9']){re.escape(k)}", padded):
                hits.append(keyword)
        better = len(hits) > len(best_hits) or (
            len(hits) == len(best_hits) and hits and PRIORITY[intent] < PRIORITY.get(best, 99)
        )
        if hits and better:
            best, best_hits = intent, hits
    return best, best_hits
