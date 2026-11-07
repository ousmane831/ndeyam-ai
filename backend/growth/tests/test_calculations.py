"""Calculs de GMD sur des valeurs de contrôle (vérifiables à la main)."""

from datetime import date, timedelta
from decimal import Decimal

from growth.calculations import WeightPoint, adg_between, growth_series, mean


def p(day, kg, method="SCALE"):
    """Mesure au jour `day` (compté depuis le 01/01/2026)."""
    return WeightPoint(date(2026, 1, 1) + timedelta(days=day), Decimal(str(kg)), method)


def test_adg_formula():
    # (26 − 20) kg / 60 j = 0,1 kg/j = 100 g/j
    value, reason = adg_between(p(0, 20), p(60, 26))
    assert value == Decimal("100.0") and reason is None


def test_weight_loss_gives_negative_adg():
    value, _ = adg_between(p(0, 30), p(10, 29))
    assert value == Decimal("-100.0")


def test_same_day_measurements_give_no_adg():
    value, reason = adg_between(p(5, 20), p(5, 21))
    assert value is None and "au moins un jour" in reason


def test_series_needs_two_measurements():
    series = growth_series([p(0, 20)])
    assert series["overall"] is None and series["intervals"] == []
    assert "deux pesées" in series["unavailable_reason"]


def test_series_intervals_and_overall_are_ordered_and_exact():
    series = growth_series([p(30, 23), p(0, 20), p(60, 27.5)])  # ordre volontairement mélangé
    assert [i["days"] for i in series["intervals"]] == [30, 30]
    assert [i["adg_g_per_day"] for i in series["intervals"]] == ["100.0", "150.0"]
    assert series["overall"]["adg_g_per_day"] == "125.0"  # 7,5 kg / 60 j
    assert series["latest_interval"]["adg_g_per_day"] == "150.0"
    assert series["overall"]["weight_change_kg"] == "7.5"


def test_visual_estimates_are_flagged_as_less_reliable():
    series = growth_series([p(0, 20), p(30, 23, "VISUAL")])
    assert series["intervals"][0]["low_reliability"] is True
    assert series["overall"]["low_reliability"] is True


def test_mean_ignores_missing_values():
    assert mean(["100", None, "150"]) == Decimal("125.0")
    assert mean([None]) is None
