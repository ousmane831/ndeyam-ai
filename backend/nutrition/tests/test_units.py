"""Conversions brut ↔ matière sèche (fonctions pures, valeurs arbitraires de contrôle)."""

from decimal import Decimal

import pytest

from nutrition.units import (
    MissingDryMatterError,
    as_fed_to_dm_kg,
    concentration_as_fed,
    dm_to_as_fed_kg,
    price_per_kg_dm,
)


def test_as_fed_to_dm():
    assert as_fed_to_dm_kg(10, 900) == Decimal("9")


def test_dm_to_as_fed_is_the_inverse():
    assert dm_to_as_fed_kg(as_fed_to_dm_kg(Decimal("3.5"), 250), 250) == Decimal("3.5")


def test_price_per_kg_dm_is_higher_than_as_fed_price():
    assert price_per_kg_dm(200, 800) == Decimal("250")


def test_concentration_on_as_fed_basis():
    assert concentration_as_fed(100, 500) == Decimal("50")


def test_unknown_dry_matter_is_never_assumed():
    with pytest.raises(MissingDryMatterError):
        as_fed_to_dm_kg(10, None)


@pytest.mark.parametrize("dm", [0, -5, 1001])
def test_invalid_dry_matter_is_rejected(dm):
    with pytest.raises(ValueError):
        dm_to_as_fed_kg(1, dm)
