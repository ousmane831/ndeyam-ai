"""Formules manuelles : analyse arithmétique sur des valeurs de CONTRÔLE (sans portée nutritionnelle)."""

from decimal import Decimal

import pytest

from farms.models import FarmMembership
from nutrition.models import IngredientPrice

pytestmark = pytest.mark.django_db

URL = "/api/v1/formulas/"


@pytest.fixture
def setup(farm, breeder, ingredient, nutrient, make_composition, client_for, ovin):
    a, b = ingredient(name="Ingrédient A"), ingredient(name="Ingrédient B")
    # Valeurs arbitraires choisies pour un calcul vérifiable à la main.
    make_composition(a, nutrient("MS"), 900)
    make_composition(a, nutrient("MAT"), 100)
    make_composition(b, nutrient("MS"), 500)
    make_composition(b, nutrient("MAT"), 200)
    IngredientPrice.objects.create(farm=farm, ingredient=a, price_per_kg_as_fed=100)
    IngredientPrice.objects.create(farm=farm, ingredient=b, price_per_kg_as_fed=50)
    return {"a": a, "b": b, "client": client_for(breeder), "farm": farm, "ovin": ovin}


def create(setup, items=None, **kw):
    items = items or [
        {"ingredient": setup["a"].pk, "quantity_as_fed_kg": "1"},
        {"ingredient": setup["b"].pk, "quantity_as_fed_kg": "2"},
    ]
    data = {
        "farm": setup["farm"].pk,
        "name": "Ration test",
        "species": setup["ovin"].pk,
        "manual_items": items,
        **kw,
    }
    return setup["client"].post(URL, data, format="json")


def test_manual_formula_analysis_is_exact(setup):
    response = create(setup)
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["mode"] == "MANUAL" and body["status"] == "DRAFT"
    assert Decimal(body["as_fed_kg_day"]) == Decimal("3")
    assert Decimal(body["dm_intake_kg_day"]) == Decimal("1.9")  # 1×0,9 + 2×0,5
    assert Decimal(body["cost_per_day"]) == Decimal("200")  # 1×100 + 2×50
    assert Decimal(body["cost_per_kg_as_fed"]) == Decimal("66.67")
    mat = next(n for n in body["result_snapshot"]["nutrients"] if n["code"] == "MAT")
    assert Decimal(mat["daily_amount"]) == Decimal("290")  # 0,9×100 + 1,0×200
    assert Decimal(mat["concentration_dm"]) == Decimal("152.6316")  # 290 / 1,9
    items = {i["ingredient_name"]: i for i in body["items"]}
    assert Decimal(items["Ingrédient A"]["inclusion_pct_dm"]) == Decimal("47.368")
    assert Decimal(items["Ingrédient B"]["inclusion_pct_as_fed"]) == Decimal("66.667")
    assert body["warnings"] == []


def test_unknown_dry_matter_is_reported_never_assumed(setup, ingredient):
    unknown = ingredient(name="Sans MS validée")
    response = create(
        setup,
        items=[
            {"ingredient": setup["a"].pk, "quantity_as_fed_kg": "1"},
            {"ingredient": unknown.pk, "quantity_as_fed_kg": "1"},
        ],
    )
    body = response.json()
    assert body["dm_intake_kg_day"] is None
    assert any("Matière sèche de « Sans MS validée » inconnue" in w for w in body["warnings"])
    assert any("Aucun prix" in w for w in body["warnings"])
    assert body["cost_per_day"] is None
    mat = next(n for n in body["result_snapshot"]["nutrients"] if n["code"] == "MAT")
    assert (
        mat["complete"] is False and mat["daily_amount"] is None and mat["missing_for"] == ["Sans MS validée"]
    )


def test_draft_and_demo_compositions_are_ignored(setup, ingredient, nutrient, make_composition):
    c = ingredient(name="Ingrédient C")
    make_composition(c, nutrient("MS"), 800, status="DRAFT", validated_at=None)
    body = create(setup, items=[{"ingredient": c.pk, "quantity_as_fed_kg": "1"}]).json()
    assert body["dm_intake_kg_day"] is None


def test_duplicate_ingredient_and_empty_formula_rejected(setup):
    dup = [{"ingredient": setup["a"].pk, "quantity_as_fed_kg": "1"}] * 2
    assert create(setup, items=dup).status_code == 400
    response = setup["client"].post(
        URL,
        {"farm": setup["farm"].pk, "name": "Vide", "species": setup["ovin"].pk, "manual_items": []},
        format="json",
    )
    assert response.status_code == 400


def test_review_workflow(setup, expert, client_for, make_user):
    formula_id = create(setup).json()["id"]
    owner = setup["client"]
    assert owner.post(f"{URL}{formula_id}/validate/").status_code == 403  # l'éleveur ne valide pas
    assert owner.post(f"{URL}{formula_id}/submit-review/").json()["status"] == "PENDING_REVIEW"
    assert client_for(expert).post(f"{URL}{formula_id}/validate/").status_code == 404  # expert non invité
    FarmMembership.objects.create(farm=setup["farm"], user=expert, role="EXPERT")
    response = client_for(expert).post(f"{URL}{formula_id}/validate/", {"comment": "Vérifiée"}, format="json")
    assert response.status_code == 200 and response.json()["status"] == "VALIDATED"


def test_changing_items_sends_formula_back_to_draft(setup, expert, client_for):
    formula_id = create(setup).json()["id"]
    FarmMembership.objects.create(farm=setup["farm"], user=expert, role="EXPERT")
    setup["client"].post(f"{URL}{formula_id}/submit-review/")
    client_for(expert).post(f"{URL}{formula_id}/validate/")
    response = setup["client"].patch(
        f"{URL}{formula_id}/",
        {"manual_items": [{"ingredient": setup["a"].pk, "quantity_as_fed_kg": "2"}]},
        format="json",
    )
    assert response.json()["status"] == "DRAFT" and response.json()["validated_at"] is None


def test_reject_requires_comment(setup, expert, client_for):
    formula_id = create(setup).json()["id"]
    FarmMembership.objects.create(farm=setup["farm"], user=expert, role="EXPERT")
    setup["client"].post(f"{URL}{formula_id}/submit-review/")
    assert client_for(expert).post(f"{URL}{formula_id}/reject/").status_code == 400


def test_compare_formulas(setup):
    first = create(setup).json()["id"]
    second = create(
        setup, items=[{"ingredient": setup["a"].pk, "quantity_as_fed_kg": "2"}], name="Autre"
    ).json()["id"]
    body = setup["client"].get(f"{URL}compare/", {"ids": f"{first},{second}"}).json()
    assert [f["cost_per_day"] for f in body["formulas"]] and len(body["formulas"]) == 2
    assert setup["client"].get(f"{URL}compare/", {"ids": str(first)}).status_code == 400


def test_formulas_are_isolated(setup, make_user, client_for):
    formula_id = create(setup).json()["id"]
    other = client_for(make_user())
    assert other.get(f"{URL}{formula_id}/").status_code == 404
    assert other.get(f"{URL}compare/", {"ids": f"{formula_id},{formula_id + 1}"}).status_code == 404
