"""Défauts trouvés à l'étape 11 : marquage DEMO des saisies, tableau de bord d'une ferme inaccessible."""

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def demo_farm(make_farm, breeder):
    return make_farm(owner=breeder, name="Ferme DEMO", is_demo=True)


@pytest.mark.parametrize("is_demo", [True, False])
def test_entries_follow_the_farm_demo_flag(client_for, breeder, make_farm, ovin, ingredient, is_demo):
    farm = make_farm(owner=breeder, is_demo=is_demo)
    client = client_for(breeder)
    group = client.post("/api/v1/groups/", {"farm": farm.pk, "name": "Lot"}, format="json").json()
    animal = client.post(
        "/api/v1/animals/",
        {"farm": farm.pk, "species": ovin.pk, "tag_number": "D-1", "sex": "M"},
        format="json",
    ).json()
    price = client.post(
        "/api/v1/ingredient-prices/",
        {"farm": farm.pk, "ingredient": ingredient(name="Catalogue").pk, "price_per_kg_as_fed": "100"},
        format="json",
    ).json()
    assert (group["is_demo"], animal["is_demo"], price["is_demo"]) == (is_demo, is_demo, is_demo)


def test_private_ingredient_of_demo_farm_is_demo(client_for, breeder, demo_farm):
    from nutrition.models import IngredientCategory

    category = IngredientCategory.objects.first()
    response = client_for(breeder).post(
        "/api/v1/ingredients/", {"name": "Fane", "category": category.pk, "farm": demo_farm.pk}, format="json"
    )
    assert response.status_code == 201 and response.json()["is_demo"] is True


def test_demo_flag_cannot_be_forced_on_a_real_farm(client_for, breeder, farm, ovin):
    response = client_for(breeder).post(
        "/api/v1/animals/",
        {"farm": farm.pk, "species": ovin.pk, "tag_number": "R-1", "sex": "M", "is_demo": True},
        format="json",
    )
    assert response.status_code == 201 and response.json()["is_demo"] is False


def test_dashboard_of_inaccessible_farm_is_not_found(client_for, make_user, farm):
    client = client_for(make_user())
    assert client.get("/api/v1/dashboard/", {"farm": farm.pk}).status_code == 404
    assert client.get("/api/v1/dashboard/", {"farm": "abc"}).status_code == 404
    assert client.get("/api/v1/dashboard/").status_code == 200
