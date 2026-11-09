"""Indicateur « prêt pour le calcul » de la liste d'ingrédients : même règle que le moteur (matière sèche)."""

import pytest

pytestmark = pytest.mark.django_db


def test_ready_for_engine_follows_dry_matter_validation(
    client_for, breeder, ingredient, nutrient, make_composition
):
    from nutrition.models import IngredientComposition

    ready = ingredient(name="Avec MS validée")
    make_composition(ready, nutrient("MS"), 900)  # validée
    draft = ingredient(name="MS en brouillon")
    IngredientComposition.objects.create(ingredient=draft, nutrient=nutrient("MS"), value=880)
    none = ingredient(name="Sans MS")
    rows = {
        r["name"]: r
        for r in client_for(breeder).get("/api/v1/ingredients/", {"page_size": 50}).json()["results"]
    }
    assert rows["Avec MS validée"]["ready_for_engine"] is True
    assert rows["MS en brouillon"]["ready_for_engine"] is False
    assert rows["Sans MS"]["ready_for_engine"] is False
    assert none is not None


def test_demo_ingredient_ready_with_demo_value(client_for, breeder, ingredient, nutrient):
    from nutrition.models import IngredientComposition

    demo = ingredient(name="Démo", is_demo=True)
    IngredientComposition.objects.create(ingredient=demo, nutrient=nutrient("MS"), value=900, is_demo=True)
    rows = {r["name"]: r for r in client_for(breeder).get("/api/v1/ingredients/").json()["results"]}
    assert rows["Démo"]["ready_for_engine"] is True
