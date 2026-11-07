"""
Calculs de croissance (fonctions pures, sans accès à la base).

    GMD (g/j) = (poids final − poids initial) / nombre de jours écoulés × 1000

Un GMD n'est calculé que si les données le permettent : au moins deux mesures, à des dates
différentes. Sinon, la raison est renvoyée et aucune valeur n'est produite.
Les mesures par estimation visuelle sont signalées comme moins fiables.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

LOW_RELIABILITY_METHODS = {"VISUAL"}


@dataclass(frozen=True)
class WeightPoint:
    on: date
    weight_kg: Decimal
    method: str = "SCALE"
    origin: str = "weighing"  # "weighing" ou "initial" (poids déclaré à l'enregistrement)


def _q(value, quantum="0.1"):
    return value.quantize(Decimal(quantum), rounding=ROUND_HALF_UP)


def adg_between(first: WeightPoint, last: WeightPoint):
    """GMD entre deux mesures, en g/jour. Retourne (valeur | None, raison | None)."""
    days = (last.on - first.on).days
    if days <= 0:
        return None, "Les deux mesures doivent être séparées d'au moins un jour."
    gain_kg = Decimal(last.weight_kg) - Decimal(first.weight_kg)
    return _q(gain_kg * Decimal(1000) / Decimal(days)), None


def growth_series(points: list[WeightPoint]) -> dict:
    """Évolution du poids, écarts entre mesures successives et GMD sur toute la période."""
    points = sorted(points, key=lambda p: p.on)
    intervals = []
    for previous, current in zip(points, points[1:], strict=False):
        adg, reason = adg_between(previous, current)
        intervals.append(
            {
                "from": previous.on,
                "to": current.on,
                "days": (current.on - previous.on).days,
                "weight_change_kg": str(Decimal(current.weight_kg) - Decimal(previous.weight_kg)),
                "adg_g_per_day": str(adg) if adg is not None else None,
                "low_reliability": bool({previous.method, current.method} & LOW_RELIABILITY_METHODS),
                "reason": reason,
            }
        )

    overall = None
    reason = None
    if len(points) < 2:
        reason = "Au moins deux pesées à des dates différentes sont nécessaires pour calculer un GMD."
    else:
        value, reason = adg_between(points[0], points[-1])
        if value is not None:
            overall = {
                "from": points[0].on,
                "to": points[-1].on,
                "days": (points[-1].on - points[0].on).days,
                "weight_change_kg": str(Decimal(points[-1].weight_kg) - Decimal(points[0].weight_kg)),
                "adg_g_per_day": str(value),
                "low_reliability": any(p.method in LOW_RELIABILITY_METHODS for p in points),
            }

    return {
        "points": [
            {"date": p.on, "weight_kg": str(p.weight_kg), "method": p.method, "origin": p.origin}
            for p in points
        ],
        "intervals": intervals,
        "overall": overall,
        "latest_interval": intervals[-1] if intervals else None,
        "unavailable_reason": reason if overall is None else None,
        "formula": "GMD = (poids final − poids initial) / nombre de jours écoulés",
    }


def mean(values):
    values = [Decimal(v) for v in values if v is not None]
    if not values:
        return None
    return _q(sum(values) / Decimal(len(values)))
