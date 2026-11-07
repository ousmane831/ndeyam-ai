import pytest
from django.utils import timezone

from conftest import rejected_by_database
from formulations.models import FeedFormula, FeedFormulaIngredient

pytestmark = pytest.mark.django_db


@pytest.fixture
def formula(farm, ovin):
    return FeedFormula.objects.create(farm=farm, name="Formule test", species=ovin, mode="ECONOMIC")


def test_new_formula_is_a_draft_not_a_recommendation(formula):
    assert formula.status == "DRAFT"


def test_demo_formula_can_never_be_validated(farm, ovin):
    with rejected_by_database():
        FeedFormula.objects.create(
            farm=farm,
            name="Démo",
            species=ovin,
            mode="ECONOMIC",
            is_demo=True,
            status="VALIDATED",
            validated_at=timezone.now(),
        )


def test_validated_formula_requires_a_validation_date(farm, ovin):
    with rejected_by_database():
        FeedFormula.objects.create(farm=farm, name="F", species=ovin, mode="ECONOMIC", status="VALIDATED")


def test_inclusion_percentage_is_bounded(formula, ingredient):
    with rejected_by_database():
        FeedFormulaIngredient.objects.create(
            formula=formula, ingredient=ingredient(), inclusion_pct_dm=101, quantity_dm_kg=1
        )


def test_ingredient_appears_once_per_formula(formula, ingredient):
    item = ingredient()
    FeedFormulaIngredient.objects.create(
        formula=formula, ingredient=item, inclusion_pct_dm=50, quantity_dm_kg=1
    )
    with rejected_by_database():
        FeedFormulaIngredient.objects.create(
            formula=formula, ingredient=item, inclusion_pct_dm=50, quantity_dm_kg=1
        )
