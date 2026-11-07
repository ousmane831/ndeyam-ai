import io

import pytest

from governance.models import SourceDocument, ValidationRecord
from nutrition.models import (
    Ingredient,
    IngredientCategory,
    IngredientComposition,
    IngredientPrice,
    NutritionalReference,
    NutritionalRequirement,
    NutritionSystem,
)

pytestmark = pytest.mark.django_db

ING = "/api/v1/ingredients/"
COMP = "/api/v1/compositions/"
PRICES = "/api/v1/ingredient-prices/"
REFS = "/api/v1/nutritional-references/"
REQS = "/api/v1/requirements/"


@pytest.fixture
def cereals():
    return IngredientCategory.objects.get(code="CEREALES")


@pytest.fixture
def real_source():
    return SourceDocument.objects.create(
        title="Analyse de laboratoire n° T-01 (test)", source_type="LAB_ANALYSIS"
    )


# --- Catalogue et ingrédients privés -----------------------------------------------------


def test_breeder_cannot_add_to_shared_catalog(client_for, breeder, cereals):
    response = client_for(breeder).post(ING, {"name": "Maïs", "category": cereals.pk}, format="json")
    assert response.status_code == 403


def test_breeder_creates_private_ingredient_visible_only_to_his_farm(
    client_for, breeder, farm, make_user, cereals
):
    response = client_for(breeder).post(
        ING, {"name": "Mélange maison", "category": cereals.pk, "farm": farm.pk}, format="json"
    )
    assert response.status_code == 201, response.json()
    assert response.json()["scope"] == "private" and response.json()["status"] == "DRAFT"
    other = client_for(make_user())
    assert other.get(ING).json()["count"] == 0
    assert other.get(f"{ING}{response.json()['id']}/").status_code == 404


def test_expert_manages_catalog(client_for, expert, cereals):
    response = client_for(expert).post(ING, {"name": "Maïs grain", "category": cereals.pk}, format="json")
    assert response.status_code == 201 and response.json()["scope"] == "catalog"


def test_status_cannot_be_forced_through_api(client_for, expert, cereals):
    response = client_for(expert).post(
        ING, {"name": "Sorgho", "category": cereals.pk, "status": "VALIDATED"}, format="json"
    )
    assert response.json()["status"] == "DRAFT"


def test_ingredient_detail_marks_unknown_nutrients_explicitly(
    client_for, breeder, ingredient, nutrient, make_composition
):
    item = ingredient(name="Son de blé")
    make_composition(item, nutrient("MS"), 880)
    table = client_for(breeder).get(f"{ING}{item.pk}/").json()["composition_table"]
    rows = {row["nutrient"]["code"]: row for row in table}
    assert rows["MS"]["known"] is True and rows["MS"]["validated_value"] == "880.0000"
    assert rows["MAT"]["known"] is False and rows["MAT"]["validated_value"] is None


# --- Circuit de validation ------------------------------------------------------------------


@pytest.fixture
def draft_comp(ingredient, nutrient, real_source):
    return IngredientComposition.objects.create(
        ingredient=ingredient(name="Tourteau d'arachide"),
        nutrient=nutrient("MAT"),
        value=450,
        source=real_source,
    )


def test_breeder_cannot_validate(client_for, breeder, draft_comp):
    response = client_for(breeder).post(f"{COMP}{draft_comp.pk}/validate/")
    assert response.status_code in (403, 404)
    draft_comp.refresh_from_db()
    assert draft_comp.status == "DRAFT"


def test_expert_validates_and_decision_is_traced(client_for, expert, draft_comp):
    response = client_for(expert).post(
        f"{COMP}{draft_comp.pk}/validate/", {"comment": "Conforme"}, format="json"
    )
    assert response.status_code == 200, response.json()
    assert response.json()["status"] == "VALIDATED" and response.json()["validated_by_email"] == expert.email
    record = ValidationRecord.objects.get(object_id=draft_comp.pk, action="VALIDATED")
    assert record.actor == expert and record.from_status == "DRAFT"


def test_cannot_validate_without_source(client_for, expert, ingredient, nutrient):
    comp = IngredientComposition.objects.create(ingredient=ingredient(), nutrient=nutrient("CA"), value=3)
    response = client_for(expert).post(f"{COMP}{comp.pk}/validate/")
    assert response.status_code == 400 and "source" in response.json()["detail"]


def test_cannot_validate_demo_data_or_demo_source(client_for, expert, ingredient, nutrient):
    demo_source = SourceDocument.objects.create(title="Source fictive", source_type="OTHER", is_demo=True)
    demo = IngredientComposition.objects.create(
        ingredient=ingredient(name="A"), nutrient=nutrient("CA"), value=3, source=demo_source, is_demo=True
    )
    response = client_for(expert).post(f"{COMP}{demo.pk}/validate/")
    assert response.status_code == 400 and "DEMO" in response.json()["detail"]


def test_reject_requires_comment(client_for, expert, draft_comp):
    client = client_for(expert)
    client.post(f"{COMP}{draft_comp.pk}/submit/")
    assert client.post(f"{COMP}{draft_comp.pk}/reject/").status_code == 400
    response = client.post(
        f"{COMP}{draft_comp.pk}/reject/", {"comment": "Valeur hors plage plausible"}, format="json"
    )
    assert response.json()["status"] == "REJECTED"


def test_editing_a_validated_value_sends_it_back_to_draft(client_for, expert, draft_comp):
    client = client_for(expert)
    client.post(f"{COMP}{draft_comp.pk}/validate/")
    response = client.patch(f"{COMP}{draft_comp.pk}/", {"value": "460"}, format="json")
    assert response.status_code == 200
    draft_comp.refresh_from_db()
    assert draft_comp.status == "DRAFT" and draft_comp.validated_at is None
    assert ValidationRecord.objects.filter(object_id=draft_comp.pk, action="REVERTED").exists()


def test_editing_only_notes_keeps_validation(client_for, expert, draft_comp):
    client = client_for(expert)
    client.post(f"{COMP}{draft_comp.pk}/validate/")
    client.patch(f"{COMP}{draft_comp.pk}/", {"notes": "Précision ajoutée"}, format="json")
    draft_comp.refresh_from_db()
    assert draft_comp.status == "VALIDATED"


def test_breeder_cannot_edit_catalog_composition(client_for, breeder, draft_comp):
    assert (
        client_for(breeder).patch(f"{COMP}{draft_comp.pk}/", {"value": "1"}, format="json").status_code == 403
    )


def test_dry_matter_range_checked_through_api(client_for, expert, ingredient, nutrient, real_source):
    response = client_for(expert).post(
        COMP,
        {
            "ingredient": ingredient().pk,
            "nutrient": nutrient("MS").pk,
            "value": "1200",
            "source": real_source.pk,
        },
        format="json",
    )
    assert response.status_code == 400


# --- Import / export CSV ------------------------------------------------------------------------


def upload(text):
    f = io.BytesIO(text.encode("utf-8"))
    f.name = "compositions.csv"
    return f


IMPORT_CSV = (
    "ingredient;categorie;nutriment;systeme;valeur\n"
    "Foin de test;FOURRAGES;MS;;870\n"
    "Foin de test;FOURRAGES;MAT;;\n"  # vide : ignoré (reste inconnu)
    "Foin de test;FOURRAGES;UFL;INRA;0,62\n"
    "Foin de test;FOURRAGES;XYZ;;12\n"  # nutriment inconnu
    "Foin de test;FOURRAGES;CA;;-1\n"  # négatif
)


def test_import_creates_drafts_and_reports_errors(client_for, expert, real_source):
    response = client_for(expert).post(
        f"{COMP}import/", {"file": upload(IMPORT_CSV), "source": real_source.pk}, format="multipart"
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["created_rows"] == 2 and body["error_rows"] == 2
    assert {e["line"] for e in body["errors"]} == {5, 6}
    hay = Ingredient.objects.get(name="Foin de test")
    assert set(hay.compositions.values_list("status", flat=True)) == {"DRAFT"}
    assert not hay.compositions.filter(nutrient__code="MAT").exists()


def test_import_never_overwrites_validated_value(
    client_for, expert, real_source, make_composition, ingredient, nutrient, cereals
):
    hay = Ingredient.objects.create(
        name="Foin de test", category=IngredientCategory.objects.get(code="FOURRAGES")
    )
    make_composition(hay, nutrient("MS"), 850, source=real_source)
    body = (
        client_for(expert)
        .post(
            f"{COMP}import/",
            {"file": upload("ingredient;nutriment;valeur\nFoin de test;MS;870\n"), "source": real_source.pk},
            format="multipart",
        )
        .json()
    )
    assert body["error_rows"] == 1 and "VALIDÉE" in body["errors"][0]["error"]
    assert hay.compositions.get(nutrient__code="MS").value == 850


def test_demo_source_cannot_feed_real_data(client_for, expert):
    demo_source = SourceDocument.objects.create(title="Fictive", source_type="OTHER", is_demo=True)
    body = (
        client_for(expert)
        .post(f"{COMP}import/", {"file": upload(IMPORT_CSV), "source": demo_source.pk}, format="multipart")
        .json()
    )
    assert body["status"] == "FAILED"
    assert not Ingredient.objects.filter(name="Foin de test").exists()


def test_breeder_cannot_import_compositions(client_for, breeder, real_source):
    response = client_for(breeder).post(
        f"{COMP}import/", {"file": upload(IMPORT_CSV), "source": real_source.pk}, format="multipart"
    )
    assert response.status_code == 403


def test_export_compositions(client_for, breeder, ingredient, nutrient, make_composition):
    make_composition(ingredient(name="Maïs"), nutrient("MS"), 880)
    content = client_for(breeder).get(f"{ING}export/").content.decode("utf-8-sig")
    assert "Maïs;CEREALES;MS;;g/kg brut;880;Validé" in content


# --- Prix ----------------------------------------------------------------------------------------


def test_prices_are_private_to_the_farm(client_for, breeder, farm, make_user, make_farm, ingredient):
    item = ingredient(name="Maïs")
    other = make_user()
    other_farm = make_farm(owner=other)
    IngredientPrice.objects.create(farm=other_farm, ingredient=item, price_per_kg_as_fed=210)
    client = client_for(breeder)
    response = client.post(
        PRICES, {"farm": farm.pk, "ingredient": item.pk, "price_per_kg_as_fed": "200"}, format="json"
    )
    assert response.status_code == 201
    assert [p["price_per_kg_as_fed"] for p in client.get(PRICES).json()["results"]] == ["200.00"]


def test_latest_price_per_ingredient(client_for, breeder, farm, ingredient):
    item = ingredient(name="Son")
    IngredientPrice.objects.create(
        farm=farm, ingredient=item, price_per_kg_as_fed=100, valid_from="2026-01-01"
    )
    IngredientPrice.objects.create(
        farm=farm, ingredient=item, price_per_kg_as_fed=120, valid_from="2026-06-01"
    )
    results = client_for(breeder).get(PRICES, {"latest": "true"}).json()["results"]
    assert [p["price_per_kg_as_fed"] for p in results] == ["120.00"]


def test_price_rejects_invalid_values(client_for, breeder, farm, ingredient, make_farm):
    client = client_for(breeder)
    item = ingredient(name="Maïs")
    assert (
        client.post(
            PRICES, {"farm": farm.pk, "ingredient": item.pk, "price_per_kg_as_fed": "0"}, format="json"
        ).status_code
        == 400
    )
    foreign = ingredient(name="Privé ailleurs", farm=make_farm())
    assert client.post(
        PRICES, {"farm": farm.pk, "ingredient": foreign.pk, "price_per_kg_as_fed": "50"}, format="json"
    ).status_code in (400, 403)


# --- Références et besoins ---------------------------------------------------------------------


@pytest.fixture
def reference(ovin, real_source):
    return NutritionalReference.objects.create(
        name="Référence de test",
        species=ovin,
        system=NutritionSystem.objects.get(code="INRA"),
        source=real_source,
    )


def test_breeder_reads_references_but_cannot_write(client_for, breeder, reference, ovin):
    client = client_for(breeder)
    assert client.get(REFS).json()["count"] == 1
    response = client.post(
        REFS, {"name": "X", "species": ovin.pk, "system": reference.system.pk}, format="json"
    )
    assert response.status_code == 403


def test_requirement_from_incompatible_system_rejected(client_for, expert, reference, nutrient):
    response = client_for(expert).post(
        REQS,
        {
            "reference": reference.pk,
            "nutrient": nutrient("EM", "NRC").pk,
            "expression": "DAILY_AMOUNT",
            "min_value": "2",
        },
        format="json",
    )
    assert response.status_code == 400 and "incompatible" in str(response.json())


def test_reference_without_requirements_cannot_be_validated(client_for, expert, reference):
    response = client_for(expert).post(f"{REFS}{reference.pk}/validate/")
    assert response.status_code == 400 and "aucun besoin" in response.json()["detail"]


def test_changing_a_requirement_reverts_validated_reference(client_for, expert, reference, nutrient):
    client = client_for(expert)
    req = client.post(
        REQS,
        {
            "reference": reference.pk,
            "nutrient": nutrient("UFL", "INRA").pk,
            "expression": "DAILY_AMOUNT",
            "min_value": "1",
        },
        format="json",
    ).json()
    assert client.post(f"{REFS}{reference.pk}/validate/").json()["status"] == "VALIDATED"
    client.patch(f"{REQS}{req['id']}/", {"min_value": "1.1"}, format="json")
    reference.refresh_from_db()
    assert reference.status == "DRAFT"


def test_requirement_min_greater_than_max_rejected(client_for, expert, reference, nutrient):
    response = client_for(expert).post(
        REQS,
        {
            "reference": reference.pk,
            "nutrient": nutrient("MAT").pk,
            "expression": "DAILY_AMOUNT",
            "min_value": "200",
            "max_value": "100",
        },
        format="json",
    )
    assert response.status_code == 400
    assert not NutritionalRequirement.objects.exists()


def test_inclusion_constraint_bounds_validated(client_for, expert, ovin, ingredient):
    url = "/api/v1/inclusion-constraints/"
    client = client_for(expert)
    assert (
        client.post(
            url, {"species": ovin.pk, "ingredient": ingredient().pk, "max_pct_dm": "130"}, format="json"
        ).status_code
        == 400
    )
    assert (
        client.post(
            url,
            {"species": ovin.pk, "ingredient": ingredient(name="B").pk, "max_pct_dm": "30"},
            format="json",
        ).status_code
        == 201
    )


# --- Sources ---------------------------------------------------------------------------------------


def test_sources_writable_by_reviewers_only(client_for, breeder, expert):
    data = {"title": "Tables locales", "source_type": "COMPOSITION_TABLE"}
    assert client_for(breeder).post("/api/v1/sources/", data, format="json").status_code == 403
    assert client_for(expert).post("/api/v1/sources/", data, format="json").status_code == 201


def test_used_source_cannot_be_deleted(client_for, expert, draft_comp, real_source):
    response = client_for(expert).delete(f"/api/v1/sources/{real_source.pk}/")
    assert response.status_code == 409
    assert response.json()["code"] == "protected"
