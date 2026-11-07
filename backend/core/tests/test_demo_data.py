"""Jeu de données DEMO : complet, entièrement marqué, jamais validé, isolé et réversible."""

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings

from core import demo_data

pytestmark = pytest.mark.django_db
PASSWORD = "Demo-Test-2026!"


@pytest.fixture
def loaded():
    with override_settings(DEBUG=True):
        call_command("load_demo_data", password=PASSWORD, stdout=open(__import__("os").devnull, "w"))
    return demo_data


def test_dataset_is_complete(loaded):
    from alerts.models import Alert
    from animals.models import Animal
    from farms.models import Farm
    from feeding.models import FeedingRecord, Ration
    from formulations.models import FeedFormula
    from growth.models import Weighing
    from knowledge_base.models import TechnicalDocument

    farms = Farm.objects.filter(is_demo=True)
    assert farms.count() == 2 and all(f.name.startswith("[DEMO]") for f in farms)
    assert Animal.objects.filter(farm__in=farms).count() == 20
    assert Weighing.objects.filter(animal__farm__in=farms).count() >= 60
    statuses = set(FeedFormula.objects.filter(farm__in=farms).values_list("status", flat=True))
    assert {"PENDING_REVIEW", "ESTIMATED", "INFEASIBLE"} <= statuses
    assert Ration.objects.filter(farm__in=farms, status="ACTIVE").count() == 1
    assert FeedingRecord.objects.filter(farm__in=farms).count() == 30
    assert FeedingRecord.objects.filter(farm__in=farms, estimated_cost__isnull=False).count() == 30
    types = set(Alert.objects.filter(farm__in=farms, status="OPEN").values_list("alert_type", flat=True))
    assert {"MISSING_DATA", "WEIGHING_REMINDER", "FORMULA_TO_REVIEW"} <= types
    doc = TechnicalDocument.objects.get(is_demo=True)
    assert doc.processing_status == "INDEXED" and doc.chunks.exists()


def test_everything_is_marked_demo_and_nothing_is_validated(loaded):
    from animals.models import Animal, AnimalGroup
    from feeding.models import FeedingRecord, Ration
    from formulations.models import FeedFormula
    from governance.models import SourceDocument
    from growth.models import Weighing
    from knowledge_base.models import TechnicalDocument
    from nutrition.models import (
        InclusionConstraint,
        Ingredient,
        IngredientComposition,
        IngredientPrice,
        NutritionalReference,
    )

    for model in (Animal, AnimalGroup, Weighing, IngredientPrice, FeedFormula, Ration, FeedingRecord):
        assert not model.objects.filter(is_demo=False).exists(), model.__name__
    for model in (
        SourceDocument,
        Ingredient,
        IngredientComposition,
        NutritionalReference,
        InclusionConstraint,
        TechnicalDocument,
    ):
        assert model.objects.exists() and not model.objects.filter(is_demo=False).exists(), model.__name__
    for model in (
        Ingredient,
        IngredientComposition,
        NutritionalReference,
        InclusionConstraint,
        TechnicalDocument,
    ):
        assert not model.objects.filter(status="VALIDATED").exists(), model.__name__
        assert not model.objects.usable_for_engine().exists(), model.__name__
    assert not FeedFormula.objects.filter(status="VALIDATED").exists()
    assert all(i.name.startswith("[DEMO]") for i in Ingredient.objects.all())
    assert all("fictive" in r.name for r in NutritionalReference.objects.all())


def test_demo_formula_is_feasible_and_flagged(loaded):
    from formulations.models import FeedFormula

    formula = FeedFormula.objects.get(name="Embouche Tabaski — économique")
    assert formula.is_demo and formula.cost_per_day is not None and formula.items.count() >= 2
    assert "DÉMONSTRATION" in formula.warnings[0]
    assert all(c["status"] == "ok" for c in formula.result_snapshot["constraints"])


def test_real_farm_never_uses_demo_data(loaded, farm, breeder, ovin, client_for):
    from nutrition.models import Ingredient

    ids = [{"ingredient": i.pk} for i in Ingredient.objects.filter(is_demo=True)]
    response = client_for(breeder).post(
        "/api/v1/formulas/calculate/",
        {
            "farm": farm.pk,
            "name": "Réelle",
            "mode": "ECONOMIC",
            "species": ovin.pk,
            "ingredients": ids,
            "save": False,
        },
        format="json",
    )
    result = response.json()["result"]
    assert result["status"] == "REFUSED"
    assert "Aucune référence nutritionnelle validée" in result["refusal_reasons"][0]


def test_demo_accounts_can_log_in_and_are_isolated(loaded, api):
    response = api.post(
        "/api/v1/auth/login/", {"email": f"eleveur2@{demo_data.DEMO_DOMAIN}", "password": PASSWORD}
    )
    assert response.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.json()['access']}")
    farms = api.get("/api/v1/farms/").json()["results"]
    assert [f["name"] for f in farms] == ["[DEMO] Élevage de Kaolack"]
    assert api.get("/api/v1/animals/").json()["count"] == 4


def test_second_load_refused_without_reset(loaded):
    with override_settings(DEBUG=True), pytest.raises(CommandError, match="déjà chargé"):
        call_command("load_demo_data", password=PASSWORD)


def test_reset_and_remove_only_touch_demo_data(loaded, farm, animal, source):
    from accounts.models import User
    from animals.models import Animal
    from farms.models import Farm

    with override_settings(DEBUG=True):
        call_command(
            "load_demo_data", reset=True, password=PASSWORD, stdout=open(__import__("os").devnull, "w")
        )
        assert Farm.objects.filter(is_demo=True).count() == 2
        call_command("load_demo_data", remove=True, stdout=open(__import__("os").devnull, "w"))
    assert not Farm.objects.filter(is_demo=True).exists()
    assert not User.objects.filter(email__endswith=demo_data.DEMO_DOMAIN).exists()
    assert Farm.objects.filter(pk=farm.pk).exists() and Animal.objects.filter(pk=animal.pk).exists()
    assert type(source).objects.filter(pk=source.pk).exists()


def test_refused_in_production_without_flag():
    with override_settings(DEBUG=False), pytest.raises(CommandError, match="allow-production"):
        call_command("load_demo_data", password=PASSWORD)


def test_no_password_in_source_code():
    import inspect

    from core.management.commands import load_demo_data

    assert "password=" not in inspect.getsource(demo_data).replace("password=password", "")
    assert "secrets.token_urlsafe" in inspect.getsource(load_demo_data)
