"""Règles communes à toute donnée de référence, vérifiées au niveau de PostgreSQL."""

import pytest
from django.utils import timezone

from conftest import rejected_by_database
from governance.models import SourceDocument

pytestmark = pytest.mark.django_db


def test_demo_data_can_never_be_validated(ingredient, validated_kwargs):
    with rejected_by_database():
        ingredient(name="Maïs DEMO", is_demo=True, **validated_kwargs)


def test_validated_data_requires_a_source(ingredient):
    with rejected_by_database():
        ingredient(name="Sans source", status="VALIDATED", validated_at=timezone.now())


def test_validated_data_requires_a_validation_date(ingredient, source):
    with rejected_by_database():
        ingredient(name="Sans date", status="VALIDATED", source=source)


def test_validated_data_with_source_and_date_is_accepted(ingredient, validated_kwargs):
    item = ingredient(name="Maïs", **validated_kwargs)
    assert item.is_usable_for_engine


def test_usable_for_engine_excludes_demo_draft_pending_and_rejected(ingredient, validated_kwargs):
    from nutrition.models import Ingredient

    ok = ingredient(name="Validé", **validated_kwargs)
    ingredient(name="Brouillon")
    ingredient(name="En attente", status="PENDING")
    ingredient(name="Rejeté", status="REJECTED")
    ingredient(name="Démo", is_demo=True, status="PENDING")
    assert list(Ingredient.objects.usable_for_engine()) == [ok]
    assert Ingredient.objects.demo().count() == 1
    assert Ingredient.objects.awaiting_validation().count() == 2


def test_source_year_must_be_plausible():
    with rejected_by_database():
        SourceDocument.objects.create(title="X", source_type="OTHER", year=3000)
