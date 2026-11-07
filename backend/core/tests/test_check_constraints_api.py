"""Valeur interdite par une contrainte CHECK : 400, jamais 500 (défaut trouvé à l'étape 11)."""

import pytest

pytestmark = pytest.mark.django_db


def test_negative_composition_value(client_for, expert, ingredient, nutrient, source):
    response = client_for(expert).post(
        "/api/v1/compositions/",
        {
            "ingredient": ingredient(name="Cat").pk,
            "nutrient": nutrient("MAT").pk,
            "value": -1,
            "source": source.pk,
        },
        format="json",
    )
    assert response.status_code == 400
    assert "Une teneur ne peut pas être négative." in str(response.json()["errors"])


def test_negative_dry_matter_intake(client_for, expert, ovin):
    from nutrition.models import NutritionSystem

    response = client_for(expert).post(
        "/api/v1/nutritional-references/",
        {
            "name": "Réf",
            "species": ovin.pk,
            "system": NutritionSystem.objects.get(code="INRA").pk,
            "dm_intake_min_kg_day": "-1",
            "dm_intake_max_kg_day": "1",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "positifs" in str(response.json()["errors"])


@pytest.mark.parametrize("year", [900, 3000])
def test_implausible_source_year(client_for, expert, year):
    response = client_for(expert).post(
        "/api/v1/sources/", {"title": "Livre", "source_type": "BOOK", "year": year}, format="json"
    )
    assert response.status_code == 400
    assert "plausible" in str(response.json()["errors"])


def test_negative_animal_weight_on_manual_formula(client_for, breeder, farm, ovin, ingredient):
    response = client_for(breeder).post(
        "/api/v1/formulas/",
        {
            "farm": farm.pk,
            "name": "Manuelle",
            "mode": "MANUAL",
            "species": ovin.pk,
            "animal_weight_kg": "-3",
            "manual_items": [{"ingredient": ingredient(name="Cat").pk, "quantity_as_fed_kg": "1"}],
        },
        format="json",
    )
    assert response.status_code == 400


def test_every_check_constraint_reachable_by_input_has_a_french_message():
    from django.apps import apps
    from django.db.models import CheckConstraint

    from core.serializers import CHECK_MESSAGES

    workflow = ("_demo_never_validated", "_validated_has_date", "_validated_has_source")
    internal = {
        "nutrient_dry_matter_in_g_per_kg_as_fed",
        "nutrient_only_dry_matter_on_as_fed_basis",
        "alert_has_audience",
        "chunk_pages_ordered",
        "formulaitem_pct_dm_range",
        "formulaitem_has_a_quantity",
        "formulaitem_pct_as_fed_range",
        "formulaitem_quantities_non_negative",
    }
    names = {c.name for m in apps.get_models() for c in m._meta.constraints if isinstance(c, CheckConstraint)}
    reachable = {n for n in names if not n.endswith(workflow) and n not in internal}
    assert reachable <= set(CHECK_MESSAGES), reachable - set(CHECK_MESSAGES)
