"""Module « Saison » : calendrier, prix et disponibilité par saison, besoins de saison, conseils validés."""

from datetime import date

import pytest
from django.utils import timezone

from formulations.tests.test_calculate_api import request, world  # noqa: F401  (fixtures réutilisées)
from nutrition.models import IngredientPrice, NutritionalReference, NutritionalRequirement
from seasons.models import IngredientAvailability, Season, SeasonalAdvice

pytestmark = pytest.mark.django_db


def test_default_calendar_covers_every_month_once():
    seasons = list(Season.objects.all())
    assert {s.code for s in seasons} == {"SECHE_FRAICHE", "SECHE_CHAUDE", "HIVERNAGE"}
    for month in range(1, 13):
        assert sum(s.contains(month) for s in seasons) == 1, month
    assert Season.for_date(date(2026, 1, 15)).code == "SECHE_FRAICHE"  # saison à cheval sur l'année
    assert Season.for_date(date(2026, 4, 1)).code == "SECHE_CHAUDE"
    assert Season.for_date(date(2026, 8, 1)).code == "HIVERNAGE"


def test_seasonal_price_and_availability_are_used_and_reported(world):  # noqa: F811
    hot = Season.objects.get(code="SECHE_CHAUDE")
    IngredientPrice.objects.create(
        farm=world["farm"],
        ingredient=world["a"],
        price_per_kg_as_fed=150,
        season=hot,
        valid_from=timezone.localdate(),
    )
    IngredientAvailability.objects.create(
        farm=world["farm"], ingredient=world["b"], season=hot, level="SCARCE"
    )
    body = request(world, season=hot.pk).json()
    prices = {i["ingredient_name"]: i["price_per_kg_as_fed"] for i in body["formula"]["items"]}
    assert prices["Ingrédient A"] == "150.00"  # prix habituel de la saison sèche chaude
    warnings = " ".join(body["result"]["warnings"])
    assert "prix habituel déclaré pour la saison" in warnings
    assert "« Ingrédient B » est déclaré rare en saison sèche chaude (soudure)." in warnings
    assert body["formula"]["season_name"] == "Saison sèche chaude (soudure)"
    # Une autre saison : le prix de saison sèche chaude ne s'applique pas.
    cool = Season.objects.get(code="SECHE_FRAICHE")
    other = request(world, season=cool.pk).json()
    assert {i["ingredient_name"]: i["price_per_kg_as_fed"] for i in other["formula"]["items"]}[
        "Ingrédient A"
    ] == "100.00"


def test_seasonal_reference_is_chosen_only_in_its_season(world, validated_kwargs, nutrient):  # noqa: F811
    hot = Season.objects.get(code="SECHE_CHAUDE")
    heat = NutritionalReference.objects.create(
        name="Référence chaleur",
        species=world["ovin"],
        system=world["inra"],
        season=hot,
        dm_intake_min_kg_day=1,
        dm_intake_max_kg_day=1,
        **validated_kwargs,
    )
    NutritionalRequirement.objects.create(
        reference=heat, nutrient=nutrient("MAT"), expression="DAILY_AMOUNT", min_value=150
    )
    assert request(world, season=hot.pk).json()["result"]["reference"]["name"] == "Référence chaleur"
    cool = Season.objects.get(code="SECHE_FRAICHE")
    assert request(world, season=cool.pk).json()["result"]["reference"]["name"] == "Référence contrôlée"


def test_only_validated_advice_reaches_farmers(world, source, make_user, client_for):  # noqa: F811
    hot = Season.objects.get(code="SECHE_CHAUDE")
    draft = SeasonalAdvice.objects.create(season=hot, title="Brouillon", text="…", source=source)
    done = SeasonalAdvice.objects.create(
        season=hot,
        title="Eau à volonté",
        text="…",
        source=source,
        status="VALIDATED",
        validated_at=timezone.now(),
    )
    body = world["client"].get(f"/api/v1/seasons/current/?farm={world['farm'].pk}&date=2026-04-10").json()
    assert body["season"]["code"] == "SECHE_CHAUDE" and body["next_season"]["code"] == "HIVERNAGE"
    assert [a["title"] for a in body["advice"]] == [done.title]
    assert draft.title not in str(body)
    # Les éleveurs ne rédigent pas les conseils : réservé aux experts et administrateurs.
    created = world["client"].post(
        "/api/v1/seasonal-advice/", {"season": hot.pk, "title": "x", "text": "y"}, format="json"
    )
    assert created.status_code == 403


def test_availability_is_isolated_by_farm(world, make_farm, make_user, client_for, ingredient):  # noqa: F811
    hot = Season.objects.get(code="SECHE_CHAUDE")
    url = "/api/v1/ingredient-availability/"
    ok = world["client"].post(
        url,
        {"farm": world["farm"].pk, "ingredient": world["a"].pk, "season": hot.pk, "level": "SCARCE"},
        format="json",
    )
    assert ok.status_code == 201 and ok.json()["level_label"] == "Rare"
    stranger = client_for(make_user())
    assert stranger.get(url).json() == []
    foreign = make_farm(owner=make_user())
    response = world["client"].post(
        url,
        {"farm": foreign.pk, "ingredient": world["a"].pk, "season": hot.pk, "level": "SCARCE"},
        format="json",
    )
    assert response.status_code == 400
