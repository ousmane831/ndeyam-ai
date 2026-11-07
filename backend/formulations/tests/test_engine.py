"""
Tests du moteur de formulation sur des jeux de données CONTRÔLÉS.

Les valeurs sont arbitraires et choisies pour que la solution optimale se calcule à la main ;
elles n'ont aucune portée nutritionnelle.
"""

import pytest

from formulations.engine import (
    InclusionBound,
    IngredientInput,
    Mode,
    NutrientSpec,
    Problem,
    RequirementSpec,
    formulate,
)
from formulations.engine.types import Expression

N_PROT = NutrientSpec(1, "PROT", "Nutriment protéique test", "g")
N_ENER = NutrientSpec(2, "ENER", "Nutriment énergétique test", "U", system="TEST")
NUTRIENTS = {1: N_PROT, 2: N_ENER}


def ingredient(id_, name, dm, prot, price, ener=None, **kw):
    composition = {1: prot}
    if ener is not None:
        composition[2] = ener
    return IngredientInput(
        id=id_,
        name=name,
        dm_g_per_kg_as_fed=dm,
        composition_per_kg_dm=composition,
        price_per_kg_as_fed=price,
        sources={1: "Source contrôlée"},
        **kw,
    )


def a():  # 100 g PROT/kg MS ; 1 kg MS coûte 100 (MS 100 %)
    return ingredient(1, "A", 1000, 100, 100)


def b():  # 300 g PROT/kg MS ; 1 kg MS coûte 300
    return ingredient(2, "B", 1000, 300, 300)


def problem(*ingredients, requirements=None, mode=Mode.ECONOMIC, dmi=(1.0, 1.0), bounds=None):
    return Problem(
        mode=mode,
        nutrients=NUTRIENTS,
        requirements=requirements
        if requirements is not None
        else [RequirementSpec(1, Expression.DAILY_AMOUNT, min_value=200)],
        ingredients=list(ingredients),
        dm_intake_min_kg=dmi[0],
        dm_intake_max_kg=dmi[1],
        inclusion_bounds=bounds or [],
        reference_label="Référence test",
        reference_source="Source contrôlée",
    )


def qty(result, name):
    return next((i["quantity_dm_kg"] for i in result.items if i["name"] == name), 0.0)


# --- Mode économique ---------------------------------------------------------------------------


def test_economic_mode_finds_cheapest_mix():
    # xA + xB = 1 ; 100 xA + 300 xB ≥ 200 → xB ≥ 0,5 ;
    # coût 100 xA + 300 xB minimal → xA = xB = 0,5 ; coût 200.
    result = formulate(problem(a(), b()))
    assert result.status == "ESTIMATED"
    assert qty(result, "A") == pytest.approx(0.5) and qty(result, "B") == pytest.approx(0.5)
    assert result.cost_per_day == pytest.approx(200)
    prot = next(n for n in result.nutrients if n["code"] == "PROT")
    assert prot["daily_amount"] == pytest.approx(200) and prot["requirements"][0]["status"] == "ok"
    assert all(c["status"] == "ok" for c in result.constraints)
    assert "Source contrôlée" in result.sources


def test_dry_matter_and_as_fed_conversions():
    # A à 50 % de MS : 0,5 kg MS = 1 kg brut ; prix 50 / kg brut = 100 / kg MS.
    wet_a = ingredient(1, "A", 500, 100, 50)
    result = formulate(problem(wet_a, b()))
    item = next(i for i in result.items if i["name"] == "A")
    assert item["quantity_dm_kg"] == pytest.approx(0.5)
    assert item["quantity_as_fed_kg"] == pytest.approx(1.0)
    assert result.as_fed_kg_day == pytest.approx(1.5)
    assert item["inclusion_pct_as_fed"] == pytest.approx(100 * 1 / 1.5)


def test_maximum_and_concentration_constraints():
    # Teneur PROT ≤ 150 g/kg MS et apport ≥ 120 g/j, ingestion libre entre 1 et 2 kg MS.
    reqs = [
        RequirementSpec(1, Expression.DAILY_AMOUNT, min_value=120),
        RequirementSpec(1, Expression.DIET_CONCENTRATION, max_value=150),
    ]
    result = formulate(problem(a(), b(), requirements=reqs, dmi=(1.0, 2.0)))
    assert result.status == "ESTIMATED"
    prot = next(n for n in result.nutrients if n["code"] == "PROT")
    assert prot["concentration_dm"] <= 150 + 1e-6 and prot["daily_amount"] >= 120 - 1e-6


def test_inclusion_bound_is_respected():
    # B limité à 30 % de la MS et PROT ≥ 150 g/j : xB = 0,25 suffit (100·0,75 + 300·0,25 = 150).
    bound = InclusionBound("B ≤ 30 %", frozenset({2}), max_pct_dm=30, source="Contrainte experte test")
    result = formulate(
        problem(
            a(),
            b(),
            requirements=[RequirementSpec(1, Expression.DAILY_AMOUNT, min_value=150)],
            bounds=[bound],
        )
    )
    assert result.status == "ESTIMATED" and qty(result, "B") == pytest.approx(0.25)
    assert "Contrainte experte test" in result.sources


def test_availability_limits_quantities():
    # B disponible à 0,2 kg/j seulement : besoin de 200 g/j impossible (max 100·0,8 + 300·0,2 = 140).
    limited_b = ingredient(2, "B", 1000, 300, 300, max_as_fed_kg_per_day=0.2)
    result = formulate(problem(a(), limited_b))
    assert result.status == "INFEASIBLE"


# --- Infaisabilité expliquée --------------------------------------------------------------------


def test_infeasible_problem_names_the_blocking_constraint_and_gap():
    # Maximum possible : 300 g/j (100 % de B). Un besoin de 400 g/j manque de 100 g/j.
    result = formulate(
        problem(a(), b(), requirements=[RequirementSpec(1, Expression.DAILY_AMOUNT, min_value=400)])
    )
    assert result.status == "INFEASIBLE" and result.items == []
    blocking = [d for d in result.infeasibility if d["key"].startswith("req:1")]
    assert blocking and blocking[0]["side"] == "min"
    assert blocking[0]["gap"] == pytest.approx(100, rel=1e-3)
    assert "il manque environ 100" in blocking[0]["explanation"]


def test_contradictory_inclusion_bounds_are_reported():
    bounds = [
        InclusionBound("A ≥ 80 %", frozenset({1}), min_pct_dm=80),
        InclusionBound("B ≥ 40 %", frozenset({2}), min_pct_dm=40),
    ]
    result = formulate(
        problem(
            a(), b(), requirements=[RequirementSpec(1, Expression.DAILY_AMOUNT, min_value=0)], bounds=bounds
        )
    )
    assert result.status == "INFEASIBLE"
    assert any(d["constraint"].startswith("Incorporation") for d in result.infeasibility)


# --- Mode équilibré -----------------------------------------------------------------------------


def test_balanced_mode_aims_for_target_rather_than_cheapest():
    # Cible 250 g/j (bornes 150–300) : 100 xA + 300 xB = 250 → xB = 0,75, même si 150 coûterait moins.
    reqs = [RequirementSpec(1, Expression.DAILY_AMOUNT, min_value=150, target_value=250, max_value=300)]
    economic = formulate(problem(a(), b(), requirements=reqs))
    balanced = formulate(problem(a(), b(), requirements=reqs, mode=Mode.BALANCED))
    assert qty(economic, "B") == pytest.approx(0.25)
    assert qty(balanced, "B") == pytest.approx(0.75)
    assert next(n for n in balanced.nutrients if n["code"] == "PROT")["daily_amount"] == pytest.approx(250)


def test_balanced_mode_works_without_prices():
    no_price_a = ingredient(1, "A", 1000, 100, None)
    reqs = [RequirementSpec(1, Expression.DAILY_AMOUNT, min_value=100, max_value=300)]
    result = formulate(problem(no_price_a, b(), requirements=reqs, mode=Mode.BALANCED))
    assert result.status == "ESTIMATED" and result.cost_per_day is None
    assert any("prix sont inconnus" in w for w in result.warnings)


# --- Refus et exclusions (jamais de valeur supposée) ---------------------------------------


def test_refuses_without_requirements():
    result = formulate(problem(a(), b(), requirements=[]))
    assert result.status == "REFUSED" and "Aucun besoin" in result.refusal_reasons[0]


def test_refuses_without_dry_matter_intake():
    result = formulate(problem(a(), b(), dmi=(None, None)))
    assert result.status == "REFUSED"
    assert any("ingestion de matière sèche" in r for r in result.refusal_reasons)


def test_ingredient_with_unknown_value_is_excluded_not_zeroed():
    unknown = IngredientInput(3, "Sans valeur PROT", 900, {}, 10)
    result = formulate(problem(a(), b(), unknown))
    assert result.status == "ESTIMATED"
    assert qty(result, "Sans valeur PROT") == 0.0
    assert result.excluded_ingredients[0]["name"] == "Sans valeur PROT"
    assert "PROT" in result.excluded_ingredients[0]["reasons"][0]


def test_ingredient_with_unknown_dry_matter_is_excluded():
    result = formulate(problem(a(), b(), IngredientInput(3, "MS inconnue", None, {1: 500}, 10)))
    assert any("matière sèche inconnue" in w for w in result.warnings)


def test_economic_mode_excludes_unpriced_ingredients_and_may_refuse():
    result = formulate(problem(ingredient(1, "A", 1000, 100, None)))
    assert result.status == "REFUSED"
    assert any("prix inconnu" in w for w in result.warnings)


def test_result_is_labelled_as_estimate():
    result = formulate(problem(a(), b()))
    assert "Estimation mathématique" in result.disclaimer
    assert result.engine_version
