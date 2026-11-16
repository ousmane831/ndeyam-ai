"""
Nombres écrits en toutes lettres pour la synthèse vocale (wolof, pulaar).

Le modèle de synthèse ne sait pas lire les chiffres (« 5,5 kilo » est entendu « 100 kilos »), mais lit
correctement les nombres écrits en mots : les réponses vocales les écrivent donc en lettres, avec des
quantités arrondies à une valeur simple à dire (demi-kilo, ou grammes par 50 sous 1 kg).
Tables à faire relire par des locuteurs natifs.
"""

from decimal import ROUND_HALF_UP, Decimal

WOLOF_UNITS = [
    "",
    "benn",
    "ñaar",
    "ñett",
    "ñeent",
    "juróom",
    "juróom benn",
    "juróom ñaar",
    "juróom ñett",
    "juróom ñeent",
]
WOLOF_TENS = {1: "fukk", 3: "fanweer"}
# Forme liée devant « téeméer » (cent) et « junni » (mille) : ñaar → ñaari, juróom benn → juróom benni…
WOLOF_LINKED = [
    "",
    "",
    "ñaari",
    "ñetti",
    "ñeenti",
    "juróomi",
    "juróom benni",
    "juróom ñaari",
    "juróom ñetti",
    "juróom ñeenti",
]

PULAAR_UNITS = ["", "go'o", "ɗiɗi", "tati", "nayi", "joyi", "jeegom", "jeeɗiɗi", "jeetati", "jeenayi"]


def _wolof_below_100(n):
    tens, unit = divmod(n, 10)
    parts = []
    if tens:
        parts.append(WOLOF_TENS.get(tens) or f"{WOLOF_UNITS[tens]} fukk")
    if unit:
        parts.append(WOLOF_UNITS[unit])
    return " ak ".join(parts)


def _wolof_below_1000(n):
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        parts.append("téeméer" if hundreds == 1 else f"{WOLOF_LINKED[hundreds]} téeméer")
    if rest:
        parts.append(_wolof_below_100(rest))
    return " ak ".join(parts)


def wolof(n: int) -> str:
    if n == 0:
        return "tus"
    thousands, rest = divmod(n, 1000)
    parts = []
    if thousands:
        if thousands == 1:
            parts.append("junni")
        elif thousands < 10:
            parts.append(f"{WOLOF_LINKED[thousands]} junni")
        else:
            parts.append(f"{_wolof_below_1000(thousands)} junni")
    if rest:
        parts.append(_wolof_below_1000(rest))
    return " ak ".join(parts)


def _pulaar_below_100(n):
    tens, unit = divmod(n, 10)
    parts = []
    if tens == 1:
        parts.append("sappo")
    elif tens == 2:
        parts.append("noogaas")
    elif tens:
        parts.append(f"capanɗe {PULAAR_UNITS[tens]}")
    if unit:
        parts.append(PULAAR_UNITS[unit])
    return " e ".join(parts)


def _pulaar_below_1000(n):
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        parts.append("teemedere" if hundreds == 1 else f"teemedde {PULAAR_UNITS[hundreds]}")
    if rest:
        parts.append(_pulaar_below_100(rest))
    return " e ".join(parts)


def pulaar(n: int) -> str:
    if n == 0:
        return "ndeke"
    thousands, rest = divmod(n, 1000)
    parts = []
    if thousands:
        parts.append("ujunere" if thousands == 1 else f"ujunaaji {_pulaar_below_1000(thousands)}")
    if rest:
        parts.append(_pulaar_below_1000(rest))
    return " e ".join(parts)


SPELLERS = {"wolof": wolof, "pulaar": pulaar}


def spell(n, language):
    return SPELLERS[language](int(n))


def spoken_quantity(kg, language, units):
    """Quantité parlée : grammes (par 50) sous 1 kg, sinon kilos au demi-kilo près."""
    kg = Decimal(str(kg))
    if kg <= 0:
        return f"{spell(0, language)} {units['kilo']}"
    if kg < 1:
        grams = int((kg * 1000 / 50).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) * 50
        return f"{spell(max(grams, 50), language)} {units['gram']}"
    halves = int((kg * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    whole, half = divmod(halves, 2)
    text = f"{spell(whole, language)} {units['kilo']}"
    return f"{text} {units['half']}" if half else text


def spoken_amount(value, language, units):
    """Montant parlé, arrondi au franc."""
    amount = int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"{spell(amount, language)} {units['currency']}"
