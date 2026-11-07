"""
Conversions entre produit brut et matière sèche (MS).

Fonctions pures, sans accès à la base : elles sont utilisées par le moteur de formulation,
les rations et l'interface. La teneur en MS est exprimée en g/kg de produit brut.
Aucune valeur par défaut n'est supposée : une teneur en MS absente lève une erreur explicite.
"""

from decimal import Decimal

GRAMS_PER_KG = Decimal("1000")


class MissingDryMatterError(ValueError):
    """La teneur en matière sèche est inconnue : aucune conversion brut ↔ MS n'est possible."""


def _dm_fraction(dm_g_per_kg_as_fed) -> Decimal:
    if dm_g_per_kg_as_fed is None:
        raise MissingDryMatterError("Teneur en matière sèche inconnue : conversion impossible.")
    dm = Decimal(str(dm_g_per_kg_as_fed))
    if not (Decimal("0") < dm <= GRAMS_PER_KG):
        raise ValueError(f"Teneur en matière sèche invalide : {dm} g/kg (attendu : 0 < MS ≤ 1000).")
    return dm / GRAMS_PER_KG


def as_fed_to_dm_kg(quantity_as_fed_kg, dm_g_per_kg_as_fed) -> Decimal:
    """Quantité brute (kg) → quantité de MS (kg)."""
    return Decimal(str(quantity_as_fed_kg)) * _dm_fraction(dm_g_per_kg_as_fed)


def dm_to_as_fed_kg(quantity_dm_kg, dm_g_per_kg_as_fed) -> Decimal:
    """Quantité de MS (kg) → quantité brute (kg)."""
    return Decimal(str(quantity_dm_kg)) / _dm_fraction(dm_g_per_kg_as_fed)


def price_per_kg_dm(price_per_kg_as_fed, dm_g_per_kg_as_fed) -> Decimal:
    """Prix au kg brut → prix au kg de MS (un kg de MS coûte plus cher qu'un kg brut)."""
    return Decimal(str(price_per_kg_as_fed)) / _dm_fraction(dm_g_per_kg_as_fed)


def concentration_as_fed(value_per_kg_dm, dm_g_per_kg_as_fed) -> Decimal:
    """Teneur exprimée par kg de MS → teneur par kg brut."""
    return Decimal(str(value_per_kg_dm)) * _dm_fraction(dm_g_per_kg_as_fed)
