from datetime import timedelta

import pytest
from django.utils import timezone

from animals.models import Animal, AnimalGroup, Breed
from farms.models import FarmMembership
from growth.models import GrowthMonitoringRange, Weighing

pytestmark = pytest.mark.django_db

W = "/api/v1/weighings/"
TODAY = timezone.localdate()


def ago(days):
    return (TODAY - timedelta(days=days)).isoformat()


@pytest.fixture
def ctx(farm, breeder, animal, client_for, make_farm, make_user, ovin):
    other = Animal.objects.create(farm=make_farm(owner=make_user()), species=ovin, tag_number="X-1", sex="F")
    return {"client": client_for(breeder), "animal": animal, "other": other, "farm": farm, "ovin": ovin}


def weigh(ctx, kg, days_ago, animal=None, **kw):
    return ctx["client"].post(
        W,
        {"animal": (animal or ctx["animal"]).pk, "weight_kg": str(kg), "weighed_on": ago(days_ago), **kw},
        format="json",
    )


# --- Saisie --------------------------------------------------------------------------------------


def test_create_weighing_with_explicit_unit(ctx):
    response = weigh(ctx, 25.4, 3)
    assert response.status_code == 201, response.json()
    assert response.json()["unit"] == "kg" and response.json()["recorded_by_email"]


@pytest.mark.parametrize("kg, days, field", [(0, 1, "weight_kg"), (25, -2, "weighed_on")])
def test_invalid_weighings_rejected(ctx, kg, days, field):
    response = weigh(ctx, kg, days)
    assert response.status_code == 400 and field in response.json()["errors"]


def test_one_weighing_per_day(ctx):
    weigh(ctx, 25, 1)
    response = weigh(ctx, 26, 1)
    assert response.status_code == 400 and "weighed_on" in response.json()["errors"]


def test_weighing_before_birth_rejected(ctx):
    ctx["animal"].birth_date = TODAY - timedelta(days=10)
    ctx["animal"].save()
    assert weigh(ctx, 5, 20).status_code == 400


def test_cannot_weigh_another_farms_animal(ctx):
    response = weigh(ctx, 30, 1, animal=ctx["other"])
    assert response.status_code == 400 and "animal" in response.json()["errors"]
    assert not Weighing.objects.exists()


def test_invited_expert_cannot_record_weighings(ctx, expert, client_for):
    FarmMembership.objects.create(farm=ctx["farm"], user=expert, role="EXPERT")
    response = client_for(expert).post(
        W, {"animal": ctx["animal"].pk, "weight_kg": "25", "weighed_on": ago(1)}, format="json"
    )
    assert response.status_code == 403


def test_archived_animal_cannot_be_weighed(ctx):
    ctx["animal"].status = "SOLD"
    ctx["animal"].save()
    assert weigh(ctx, 25, 1).status_code == 400


def test_weighings_list_is_isolated(ctx):
    Weighing.objects.create(animal=ctx["other"], weight_kg=40)
    weigh(ctx, 25, 1)
    assert ctx["client"].get(W).json()["count"] == 1


# --- Séance de pesée ------------------------------------------------------------------------------


def test_bulk_session_is_all_or_nothing(ctx, ovin):
    second = Animal.objects.create(farm=ctx["farm"], species=ovin, tag_number="SN-002", sex="F")
    bad = ctx["client"].post(
        f"{W}bulk/",
        {
            "weighed_on": ago(1),
            "entries": [
                {"animal": ctx["animal"].pk, "weight_kg": "30"},
                {"animal": second.pk, "weight_kg": "0"},
            ],
        },
        format="json",
    )
    assert bad.status_code == 400 and "1" in bad.json()["errors"]
    assert not Weighing.objects.exists()
    ok = ctx["client"].post(
        f"{W}bulk/",
        {
            "weighed_on": ago(1),
            "method": "TAPE",
            "entries": [
                {"animal": ctx["animal"].pk, "weight_kg": "30"},
                {"animal": second.pk, "weight_kg": "28"},
            ],
        },
        format="json",
    )
    assert ok.status_code == 201 and len(ok.json()) == 2
    assert set(Weighing.objects.values_list("method", flat=True)) == {"TAPE"}


def test_bulk_rejects_foreign_animal(ctx):
    response = ctx["client"].post(
        f"{W}bulk/",
        {"weighed_on": ago(1), "entries": [{"animal": ctx["other"].pk, "weight_kg": "30"}]},
        format="json",
    )
    assert response.status_code == 400
    assert not Weighing.objects.exists()


# --- Courbe et GMD ------------------------------------------------------------------------------


def test_animal_growth_uses_declared_initial_weight(ctx):
    animal = ctx["animal"]
    animal.initial_weight_kg = 20
    animal.registered_on = TODAY - timedelta(days=60)
    animal.save()
    weigh(ctx, 26, 0)
    body = ctx["client"].get(f"/api/v1/growth/animals/{animal.pk}/").json()
    assert body["points"][0]["origin"] == "initial"
    assert body["overall"]["adg_g_per_day"] == "100.0"
    assert body["monitoring_range"] is None and body["latest_vs_range"] is None
    assert "Aucune plage de suivi validée" in body["monitoring_note"]


def test_growth_of_other_farm_animal_is_hidden(ctx):
    assert ctx["client"].get(f"/api/v1/growth/animals/{ctx['other'].pk}/").status_code == 404


@pytest.fixture
def ranges(ovin, validated_kwargs):
    breed = Breed.objects.get(species=ovin, name="Touabire")
    generic = GrowthMonitoringRange.objects.create(
        name="Générique (test)", species=ovin, adg_min_g=50, adg_max_g=300, **validated_kwargs
    )
    specific = GrowthMonitoringRange.objects.create(
        name="Touabire (test)", species=ovin, breed=breed, adg_min_g=150, adg_max_g=250, **validated_kwargs
    )
    GrowthMonitoringRange.objects.create(name="Brouillon", species=ovin, adg_min_g=500)
    return {"generic": generic, "specific": specific, "breed": breed}


def test_most_specific_validated_range_is_used(ctx, ranges):
    animal = ctx["animal"]
    animal.breed = ranges["breed"]
    animal.save()
    weigh(ctx, 20, 30)
    weigh(ctx, 23, 0)  # 100 g/j : dans la plage générique, sous la plage Touabire
    body = ctx["client"].get(f"/api/v1/growth/animals/{animal.pk}/").json()
    assert body["monitoring_range"]["name"] == "Touabire (test)"
    assert body["latest_vs_range"] == "below"
    assert "pas d'un diagnostic vétérinaire" in body["monitoring_note"]


def test_age_bounded_range_not_applied_when_age_unknown(ctx, ovin, validated_kwargs):
    GrowthMonitoringRange.objects.create(
        name="Jeunes", species=ovin, age_max_days=120, adg_min_g=100, **validated_kwargs
    )
    weigh(ctx, 20, 30)
    weigh(ctx, 21, 0)
    assert ctx["client"].get(f"/api/v1/growth/animals/{ctx['animal'].pk}/").json()["monitoring_range"] is None


def test_group_growth_mean_only_counts_measurable_animals(ctx, ovin):
    group = AnimalGroup.objects.create(farm=ctx["farm"], name="Lot")
    ctx["animal"].group = group
    ctx["animal"].save()
    lonely = Animal.objects.create(farm=ctx["farm"], species=ovin, tag_number="L-1", sex="F", group=group)
    weigh(ctx, 20, 30)
    weigh(ctx, 23, 0)
    weigh(ctx, 18, 0, animal=lonely)
    body = ctx["client"].get(f"/api/v1/growth/groups/{group.pk}/").json()
    assert body["animals_count"] == 2 and body["animals_with_adg"] == 1
    assert body["mean_adg_g_per_day"] == "100.0"


def test_overview_and_prediction_status(ctx):
    weigh(ctx, 25, 2)
    overview = ctx["client"].get("/api/v1/growth/overview/").json()
    assert overview["weighings_last_30_days"] == 1 and overview["animals_never_weighed"] == 0
    status = ctx["client"].get("/api/v1/growth/prediction-status/").json()
    assert status["available"] is False and "Aucun modèle" in status["reason"]


def test_weighings_export(ctx):
    weigh(ctx, 25.5, 2)
    content = ctx["client"].get(f"{W}export/").content.decode("utf-8-sig")
    assert content.splitlines()[0].startswith("animal;espece;race") and "25,5" in content


# --- Plages de suivi ------------------------------------------------------------------------------


def test_growth_ranges_managed_by_reviewers(client_for, breeder, expert, ovin, source):
    url = "/api/v1/growth-ranges/"
    data = {
        "name": "Plage test",
        "species": ovin.pk,
        "adg_min_g": "80",
        "adg_max_g": "200",
        "source": source.pk,
    }
    assert client_for(breeder).post(url, data, format="json").status_code == 403
    created = client_for(expert).post(url, data, format="json")
    assert created.status_code == 201 and created.json()["status"] == "DRAFT"
    validated = client_for(expert).post(f"{url}{created.json()['id']}/validate/")
    assert validated.json()["status"] == "VALIDATED"
    assert client_for(expert).post(url, {**data, "adg_min_g": "300"}, format="json").status_code == 400
