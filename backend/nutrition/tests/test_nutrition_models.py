from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from conftest import rejected_by_database
from nutrition.models import (
    InclusionConstraint,
    IngredientComposition,
    IngredientPrice,
    Nutrient,
    NutritionalReference,
    NutritionalRequirement,
    NutritionSystem,
)

pytestmark = pytest.mark.django_db


# --- Définitions initiales ---------------------------------------------------------------


def test_seed_contains_definitions_but_no_nutritional_values():
    assert Nutrient.objects.filter(system=None, code__in=["MS", "MAT", "CA", "P", "NDF"]).count() == 5
    assert set(NutritionSystem.objects.values_list("code", flat=True)) == {"INRA", "NRC"}
    # Aucune valeur inventée : ni composition, ni besoin, ni référence.
    assert IngredientComposition.objects.count() == 0
    assert NutritionalRequirement.objects.count() == 0
    assert NutritionalReference.objects.count() == 0


def test_dry_matter_is_expressed_on_as_fed_basis_everything_else_on_dm(nutrient):
    assert nutrient("MS").unit_label == "g/kg brut"
    assert nutrient("MAT").unit_label == "g/kg MS"
    assert nutrient("UFL", "INRA").unit_label == "UFL/kg MS"


# --- Nutriments -------------------------------------------------------------------------


def test_only_dry_matter_may_use_as_fed_basis():
    with rejected_by_database():
        Nutrient.objects.create(code="X", name="X", category="PROTEIN", amount_unit="g", basis="AS_FED")


def test_universal_nutrient_code_is_unique():
    with rejected_by_database():
        Nutrient.objects.create(code="MAT", name="Doublon", category="PROTEIN", amount_unit="g")


def test_same_code_allowed_in_different_systems():
    other = NutritionSystem.objects.create(code="AUTRE", name="Autre système")
    Nutrient.objects.create(
        code="PDI", name="PDI autre système", category="PROTEIN", amount_unit="g", system=other
    )
    assert Nutrient.objects.filter(code="PDI").count() == 2


# --- Ingrédients et compositions -------------------------------------------------------


def test_ingredient_name_unique_in_catalog_case_insensitive(ingredient):
    ingredient(name="Maïs")
    with rejected_by_database():
        ingredient(name="MAÏS")


def test_private_ingredient_may_reuse_a_catalog_name(ingredient, farm):
    ingredient(name="Son de blé")
    ingredient(name="Son de blé", farm=farm)


def test_composition_value_cannot_be_negative(ingredient, nutrient):
    with rejected_by_database():
        IngredientComposition.objects.create(ingredient=ingredient(), nutrient=nutrient("MAT"), value=-1)


def test_only_one_validated_value_per_ingredient_and_nutrient(
    ingredient, nutrient, validated_kwargs, make_user
):
    from governance.models import SourceDocument

    item = ingredient()
    IngredientComposition.objects.create(
        ingredient=item, nutrient=nutrient("MAT"), value=100, **validated_kwargs
    )
    other_source = SourceDocument.objects.create(title="Autre source", source_type="OTHER")
    # Une seconde valeur peut exister (en brouillon) depuis une autre source…
    IngredientComposition.objects.create(
        ingredient=item, nutrient=nutrient("MAT"), value=110, source=other_source
    )
    # …mais pas une seconde valeur validée.
    with rejected_by_database():
        IngredientComposition.objects.filter(source=other_source).update(
            status="VALIDATED", validated_at=validated_kwargs["validated_at"]
        )


def test_same_source_cannot_give_two_values(ingredient, nutrient, source):
    item = ingredient()
    IngredientComposition.objects.create(ingredient=item, nutrient=nutrient("CA"), value=1, source=source)
    with rejected_by_database():
        IngredientComposition.objects.create(ingredient=item, nutrient=nutrient("CA"), value=2, source=source)


@pytest.mark.parametrize("value", [Decimal("0"), Decimal("1000.1")])
def test_dry_matter_content_must_be_between_0_and_1000(ingredient, nutrient, value):
    composition = IngredientComposition(ingredient=ingredient(), nutrient=nutrient("MS"), value=value)
    with pytest.raises(ValidationError):
        composition.full_clean()


# --- Prix ----------------------------------------------------------------------------------


def test_price_must_be_positive(farm, ingredient):
    with rejected_by_database():
        IngredientPrice.objects.create(farm=farm, ingredient=ingredient(), price_per_kg_as_fed=0)


def test_price_cannot_use_another_farms_private_ingredient(farm, make_farm, ingredient):
    private = ingredient(name="Mélange maison", farm=make_farm())
    price = IngredientPrice(farm=farm, ingredient=private, price_per_kg_as_fed=150)
    with pytest.raises(ValidationError):
        price.full_clean()


# --- Références et besoins -------------------------------------------------------------


@pytest.fixture
def inra_reference(ovin):
    return NutritionalReference.objects.create(
        name="Référence de test", species=ovin, system=NutritionSystem.objects.get(code="INRA")
    )


def test_requirement_rejects_a_nutrient_from_another_system(inra_reference, nutrient):
    requirement = NutritionalRequirement(
        reference=inra_reference, nutrient=nutrient("EM", "NRC"), expression="DAILY_AMOUNT", min_value=1
    )
    with pytest.raises(ValidationError) as exc:
        requirement.full_clean()
    assert "incompatible" in str(exc.value)


def test_requirement_accepts_system_and_universal_nutrients(inra_reference, nutrient):
    for code, system in (("UFL", "INRA"), ("MAT", None)):
        NutritionalRequirement(
            reference=inra_reference, nutrient=nutrient(code, system), expression="DAILY_AMOUNT", min_value=1
        ).full_clean()


def test_requirement_needs_at_least_one_value(inra_reference, nutrient):
    with rejected_by_database():
        NutritionalRequirement.objects.create(
            reference=inra_reference, nutrient=nutrient("MAT"), expression="DAILY_AMOUNT"
        )


def test_requirement_min_cannot_exceed_max(inra_reference, nutrient):
    with rejected_by_database():
        NutritionalRequirement.objects.create(
            reference=inra_reference,
            nutrient=nutrient("MAT"),
            expression="DAILY_AMOUNT",
            min_value=200,
            max_value=100,
        )


def test_requirement_unit_label(inra_reference, nutrient):
    daily = NutritionalRequirement(
        reference=inra_reference, nutrient=nutrient("UFL", "INRA"), expression="DAILY_AMOUNT"
    )
    conc = NutritionalRequirement(
        reference=inra_reference, nutrient=nutrient("CA"), expression="DIET_CONCENTRATION"
    )
    assert daily.unit_label == "UFL/jour"
    assert conc.unit_label == "g/kg MS"


def test_reference_weight_range_must_be_ordered(ovin):
    with rejected_by_database():
        NutritionalReference.objects.create(
            name="Incohérente",
            species=ovin,
            system=NutritionSystem.objects.get(code="INRA"),
            weight_min_kg=40,
            weight_max_kg=20,
        )


# --- Contraintes d'incorporation --------------------------------------------------------


def test_inclusion_constraint_targets_exactly_one_thing(ovin, ingredient):
    from nutrition.models import IngredientCategory

    with rejected_by_database():
        InclusionConstraint.objects.create(
            species=ovin,
            ingredient=ingredient(),
            ingredient_category=IngredientCategory.objects.first(),
            max_pct_dm=30,
        )


def test_inclusion_bounds_are_percentages(ovin, ingredient):
    with rejected_by_database():
        InclusionConstraint.objects.create(species=ovin, ingredient=ingredient(), max_pct_dm=120)
