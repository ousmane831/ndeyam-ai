"""
Traduction des messages du serveur selon la langue demandée (en-tête Accept-Language).

Les messages sont écrits en français dans le code et certains sont ENREGISTRÉS tels quels (avertissements et
refus du moteur dans les formules, titres et messages des alertes) : une traduction au moment de la création
ne couvrirait pas l'historique. Ils sont donc traduits à la sortie de l'API, à partir d'un catalogue :
- `EXACT` : phrases fixes ;
- `PATTERNS` : phrases avec des parties variables (noms, nombres), en expressions régulières à groupes
  nommés ; chaque partie capturée est elle-même traduite si elle correspond au catalogue (listes de motifs
  séparés par « ; » ou « , » comprises).
Une phrase absente du catalogue reste en français : jamais de message vide ni inventé. Les données saisies par
les utilisateurs (noms, observations, documents…) ne sont jamais traduites.
"""

import re
from functools import lru_cache

from django.utils.translation import get_language

# Champs qui portent des données saisies par les utilisateurs ou des contenus documentaires.
USER_DATA_KEYS = frozenset(
    {
        "name",
        "email",
        "first_name",
        "last_name",
        "tag_number",
        "notes",
        "observations",
        "description",
        "local_names",
        "content",
        "answer",
        "question",
        "text",
        "excerpt",
        "citation",
        "url",
        "file",
        "comment",
        "review_comment",
        "reference_label",
        "reference_source",
        "ingredient_name",
        "animal_name",
        "farm_name",
        "group_name",
        "actor",
    }
)
MAX_LENGTH = 2000


@lru_cache(maxsize=1)
def _catalog():
    from .locale_en import EXACT, PATTERNS

    return EXACT, [(re.compile(pattern + r"\Z", re.S), template) for pattern, template in PATTERNS]


def _fragment(value, depth):
    """Partie variable d'une phrase : traduite si elle figure au catalogue, sinon laissée telle quelle."""
    if not value or depth > 3:
        return value
    translated = translate_text(value, depth)
    if translated != value:
        return translated
    for sep in (" ; ", ", "):
        if sep in value:
            parts = value.split(sep)
            out = [translate_text(p, depth) for p in parts]
            if out != parts:
                return sep.join(out)
    return value


def translate_text(value, depth=0):
    if not isinstance(value, str) or not value or len(value) > MAX_LENGTH:
        return value
    exact, patterns = _catalog()
    hit = exact.get(value)
    if hit is not None:
        return hit
    for regex, template in patterns:
        match = regex.match(value)
        if match:
            groups = {k: _fragment(v, depth + 1) for k, v in match.groupdict().items()}
            return template.format(**groups)
    return value


def translate_tree(data, key=None):
    """Traduit récursivement les chaînes d'une réponse (dictionnaires, listes), hors données utilisateur."""
    if isinstance(data, str):
        return data if key in USER_DATA_KEYS else translate_text(data)
    if isinstance(data, dict):
        return {k: translate_tree(v, k) for k, v in data.items()}
    if isinstance(data, list | tuple):
        return [translate_tree(v, key) for v in data]
    return data


def wants_english():
    return (get_language() or "fr").startswith("en")
