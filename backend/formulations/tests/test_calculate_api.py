"""
Calcul de formules par l'API, de la base de données au moteur.

Jeux de données CONTRÔLÉS (valeurs arbitraires, sans portée nutritionnelle) : MS à 1000 g/kg pour
que brut = MS, et une solution vérifiable à la main (voir test_engine.py).
"""

import pytest
from django.utils import timezone

from farms.models import FarmMembership
from formulations.models import FeedFormula
from nutrition.models import (
    InclusionConstraint,
    IngredientCategory,
    IngredientComposition,
    IngredientPrice,
    NutritionalReference,
    NutritionalRequirement,
    NutritionSystem,
)

pytestmark = pytest.mark.django_db
URL = "/api/v1/formulas/calculate/"


@pytest.fixture
def world(farm, breeder, ovin, ingredient, nutrient, make_composition, validated_kwargs, client_for):
    inra = NutritionSystem.objects.get(code="INRA")
    reference = NutritionalReference.objects.create(
        name="Référence contrôlée",
        species=ovin,
        system=inra,
        dm_intake_min_kg_day=1,
        dm_intake_max_kg_day=1,
        **validated_kwargs,
    )
    NutritionalRequirement.objects.create(
        reference=reference, nutrient=nutrient("MAT"), expression="DAILY_AMOUNT", min_value=200
    )
    a, b = ingredient(name="Ingrédient A"), ingredient(name="Ingrédient B")
    for item, mat, price in ((a, 100, 100), (b, 300, 300)):
        make_composition(item, nutrient("MS"), 1000)
        make_composition(item, nutrient("MAT"), mat)
        IngredientPrice.objects.create(farm=farm, ingredient=item, price_per_kg_as_fed=price)
    return {
        "client": client_for(breeder),
        "farm": farm,
        "ovin": ovin,
        "reference": reference,
        "a": a,
        "b": b,
        "inra": inra,
    }


def request(world, **kw):
    data = {
        "farm": world["farm"].pk,
        "name": "Calcul test",
        "mode": "ECONOMIC",
        "species": world["ovin"].pk,
        "ingredients": [{"ingredient": world["a"].pk}, {"ingredient": world["b"].pk}],
        **kw,
    }
    data = {k: v for k, v in data.items() if v is not None}  # None = champ omis
    return world["client"].post(URL, data, format="json")


def test_economic_calculation_is_persisted_as_estimate(world):
    response = request(world)
    assert response.status_code == 201, response.json()
    formula, result = response.json()["formula"], response.json()["result"]
    assert formula["status"] == "ESTIMATED" and formula["mode"] == "ECONOMIC"
    assert formula["cost_per_day"] == "200.00" and formula["dm_intake_kg_day"] == "1.000"
    assert {i["ingredient_name"]: i["inclusion_pct_dm"] for i in formula["items"]} == {
        "Ingrédient A": "50.000",
        "Ingrédient B": "50.000",
    }
    assert result["reference"]["name"] == "Référence contrôlée"
    assert "Référence retenue automatiquement" in result["warnings"][0]
    assert all(c["status"] == "ok" for c in result["constraints"])
    assert "Estimation mathématique" in result["disclaimer"]
    assert any(src.startswith("Source de test contrôlée") for src in result["sources"])


def test_dry_run_does_not_save(world):
    response = request(world, save=False)
    assert response.status_code == 200 and response.json()["formula"] is None
    assert response.json()["result"]["status"] == "ESTIMATED"
    assert not FeedFormula.objects.exists()


def test_draft_reference_is_never_used(world, ovin):
    world["reference"].status, world["reference"].validated_at = "DRAFT", None
    world["reference"].save()
    result = request(world).json()["result"]
    assert result["status"] == "REFUSED"
    assert "Aucune référence nutritionnelle validée" in result["refusal_reasons"][0]
    assert request(world, reference=world["reference"].pk).status_code == 400


def test_draft_compositions_are_ignored(world, ingredient, nutrient):
    c = ingredient(name="Ingrédient C (brouillon)")
    IngredientComposition.objects.create(ingredient=c, nutrient=nutrient("MS"), value=900)
    IngredientComposition.objects.create(ingredient=c, nutrient=nutrient("MAT"), value=500)
    result = request(world, ingredients=[{"ingredient": c.pk}]).json()["result"]
    assert result["status"] == "REFUSED"
    assert "matière sèche inconnue" in result["excluded_ingredients"][0]["reasons"][0]


def test_nutrients_of_another_system_are_never_mixed(world, nutrient, make_composition):
    # La référence est INRA et exige des UFL ; l'ingrédient n'a qu'une valeur NRC (EM) : il est exclu.
    NutritionalRequirement.objects.create(
        reference=world["reference"], nutrient=nutrient("UFL", "INRA"), expression="DAILY_AMOUNT", min_value=1
    )
    for item in (world["a"], world["b"]):
        make_composition(item, nutrient("EM", "NRC"), 3)
    result = request(world).json()["result"]
    assert result["status"] == "REFUSED"
    assert all("UFL" in e["reasons"][0] for e in result["excluded_ingredients"])


def test_real_farm_never_uses_demo_data(world, ingredient, nutrient):
    demo = ingredient(name="Ingrédient DEMO", is_demo=True)
    result = request(
        world,
        ingredients=[{"ingredient": world["a"].pk}, {"ingredient": world["b"].pk}, {"ingredient": demo.pk}],
    ).json()["result"]
    assert result["status"] == "ESTIMATED"
    assert any("donnée DEMO interdite" in w for w in result["warnings"])
    assert "Ingrédient DEMO" not in [i["name"] for i in result["items"]]


def test_demo_farm_uses_only_demo_data_and_cannot_be_validated(
    make_farm, make_user, client_for, ovin, nutrient, ingredient, expert
):
    owner = make_user()
    demo_farm = make_farm(owner=owner, name="Ferme DEMO", is_demo=True)
    reference = NutritionalReference.objects.create(
        name="Référence DEMO",
        species=ovin,
        is_demo=True,
        system=NutritionSystem.objects.get(code="INRA"),
        dm_intake_min_kg_day=1,
        dm_intake_max_kg_day=1,
    )
    NutritionalRequirement.objects.create(
        reference=reference, nutrient=nutrient("MAT"), expression="DAILY_AMOUNT", min_value=150
    )
    demo_ing = ingredient(name="Mélange DEMO", is_demo=True)
    IngredientComposition.objects.create(
        ingredient=demo_ing, nutrient=nutrient("MS"), value=1000, is_demo=True
    )
    IngredientComposition.objects.create(
        ingredient=demo_ing, nutrient=nutrient("MAT"), value=200, is_demo=True
    )
    IngredientPrice.objects.create(farm=demo_farm, ingredient=demo_ing, price_per_kg_as_fed=50, is_demo=True)
    client = client_for(owner)
    body = client.post(
        URL,
        {
            "farm": demo_farm.pk,
            "name": "Démo",
            "mode": "ECONOMIC",
            "species": ovin.pk,
            "ingredients": [{"ingredient": demo_ing.pk}],
        },
        format="json",
    ).json()
    assert body["formula"]["is_demo"] is True and body["formula"]["status"] == "ESTIMATED"
    assert body["result"]["warnings"][0].startswith("Calcul de DÉMONSTRATION")
    FarmMembership.objects.create(farm=demo_farm, user=expert, role="EXPERT")
    fid = body["formula"]["id"]
    client.post(f"/api/v1/formulas/{fid}/submit-review/")
    response = client_for(expert).post(f"/api/v1/formulas/{fid}/validate/")
    assert response.status_code == 400 and "DEMO" in response.json()["detail"]


def test_infeasible_result_is_saved_with_diagnosis_and_cannot_be_reviewed(world, nutrient):
    NutritionalRequirement.objects.filter(reference=world["reference"]).update(min_value=400)
    body = request(world).json()
    assert body["formula"]["status"] == "INFEASIBLE" and body["formula"]["items"] == []
    assert body["result"]["infeasibility"][0]["gap"] == pytest.approx(100, rel=1e-3)
    response = world["client"].post(f"/api/v1/formulas/{body['formula']['id']}/submit-review/")
    assert response.status_code == 400


def test_balanced_mode_through_api(world):
    NutritionalRequirement.objects.filter(reference=world["reference"]).update(
        min_value=150, target_value=250, max_value=300
    )
    items = {i["ingredient_name"]: i for i in request(world, mode="BALANCED").json()["formula"]["items"]}
    assert items["Ingrédient B"]["inclusion_pct_dm"] == "75.000"


def test_validated_inclusion_constraint_is_applied(world, validated_kwargs):
    category = IngredientCategory.objects.get(code="CEREALES")
    InclusionConstraint.objects.create(
        species=world["ovin"], ingredient_category=category, max_pct_dm=40, **validated_kwargs
    )
    # A et B sont des céréales : ensemble ≤ 40 % de la MS alors qu'ils sont les seuls
    # ingrédients → impossible.
    body = request(world).json()
    assert body["formula"]["status"] == "INFEASIBLE"
    assert any("Incorporation" in d["constraint"] for d in body["result"]["infeasibility"])


def test_price_override_and_availability(world):
    response = request(
        world,
        ingredients=[
            {"ingredient": world["a"].pk, "price_per_kg_as_fed": "150"},
            {"ingredient": world["b"].pk, "available_kg_as_fed": "30"},
        ],
    )
    assert response.status_code == 400 and "number_of_animals" in response.json()["errors"]
    body = request(
        world,
        number_of_animals=10,
        duration_days=10,
        ingredients=[
            {"ingredient": world["a"].pk, "price_per_kg_as_fed": "150"},
            {
                "ingredient": world["b"].pk,
                "available_kg_as_fed": "30",
            },  # 30 kg / (10 animaux × 10 j) = 0,3 kg/j < 0,5 kg/j nécessaires
        ],
    ).json()
    assert body["formula"]["status"] == "INFEASIBLE"
    assert any("saisi pour ce calcul" in w for w in body["result"]["warnings"])


def test_animal_profile_prefills_and_selects_weight_bounded_reference(
    world, animal, validated_kwargs, nutrient
):
    heavy = NutritionalReference.objects.create(
        name="Référence 30-40 kg",
        species=world["ovin"],
        system=world["inra"],
        weight_min_kg=30,
        weight_max_kg=40,
        dm_intake_min_kg_day=1,
        dm_intake_max_kg_day=1,
        **validated_kwargs,
    )
    NutritionalRequirement.objects.create(
        reference=heavy, nutrient=nutrient("MAT"), expression="DAILY_AMOUNT", min_value=150
    )
    animal.initial_weight_kg = 35
    animal.save()
    body = request(world, animal=animal.pk, species=None).json()
    assert body["result"]["reference"]["name"] == "Référence 30-40 kg"
    assert body["formula"]["animal_weight_kg"] == "35.00"


def test_calculation_is_isolated(world, make_farm, make_user, ingredient):
    foreign_farm = make_farm(owner=make_user())
    assert request(world, farm=foreign_farm.pk).status_code == 400
    private = ingredient(name="Privé ailleurs", farm=foreign_farm)
    response = request(world, ingredients=[{"ingredient": private.pk}])
    assert response.status_code == 400 and "autre exploitation" in str(response.json())


def test_estimated_formula_can_be_validated_by_invited_expert(world, expert, client_for):
    fid = request(world).json()["formula"]["id"]
    FarmMembership.objects.create(farm=world["farm"], user=expert, role="EXPERT")
    world["client"].post(f"/api/v1/formulas/{fid}/submit-review/")
    response = client_for(expert).post(
        f"/api/v1/formulas/{fid}/validate/", {"comment": "Vérifiée"}, format="json"
    )
    assert response.status_code == 200 and response.json()["status"] == "VALIDATED"
    assert FeedFormula.objects.get(pk=fid).validated_at <= timezone.now()
