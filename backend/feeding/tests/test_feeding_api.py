from decimal import Decimal

import pytest

from animals.models import AnimalGroup
from formulations.models import FeedFormula

pytestmark = pytest.mark.django_db

RATIONS = "/api/v1/rations/"
RECORDS = "/api/v1/feeding-records/"


@pytest.fixture
def ctx(farm, breeder, animal, ovin, client_for, make_farm, make_user):
    formula = FeedFormula.objects.create(
        farm=farm,
        name="Formule",
        species=ovin,
        mode="MANUAL",
        cost_per_kg_as_fed=Decimal("80"),
        currency="XOF",
    )
    other_farm = make_farm(owner=make_user())
    foreign_formula = FeedFormula.objects.create(farm=other_farm, name="Autre", species=ovin, mode="MANUAL")
    group = AnimalGroup.objects.create(farm=farm, name="Lot 1")
    return {
        "client": client_for(breeder),
        "farm": farm,
        "animal": animal,
        "formula": formula,
        "foreign_formula": foreign_formula,
        "group": group,
    }


def ration(ctx, **kw):
    data = {
        "farm": ctx["farm"].pk,
        "name": "Ration de croissance",
        "formula": ctx["formula"].pk,
        "animal": ctx["animal"].pk,
        "start_date": "2026-10-01",
        "planned_as_fed_kg_per_animal_day": "1.5",
        **kw,
    }
    return ctx["client"].post(RATIONS, data, format="json")


def test_create_ration_and_end_it(ctx):
    response = ration(ctx)
    assert response.status_code == 201, response.json()
    rid = response.json()["id"]
    assert (
        ctx["client"].post(f"{RATIONS}{rid}/end/", {"end_date": "2026-09-01"}, format="json").status_code
        == 400
    )
    ended = ctx["client"].post(f"{RATIONS}{rid}/end/", {"end_date": "2026-11-01"}, format="json").json()
    assert ended["status"] == "ENDED"


def test_ration_needs_exactly_one_target(ctx):
    assert ration(ctx, group=ctx["group"].pk).status_code == 400
    assert ration(ctx, animal=None).status_code == 400


def test_ration_cannot_use_another_farms_formula(ctx):
    response = ration(ctx, formula=ctx["foreign_formula"].pk)
    assert response.status_code == 400


def test_feeding_record_derives_calculated_quantity_and_cost(ctx):
    rid = ration(ctx).json()["id"]
    response = ctx["client"].post(
        RECORDS,
        {"farm": ctx["farm"].pk, "ration": rid, "fed_on": "2026-11-02", "quantity_distributed_kg": "1.6"},
        format="json",
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["quantity_calculated_kg"] == "1.500"  # prévu par la ration
    assert body["quantity_consumed_kg"] is None  # jamais supposé
    assert body["estimated_cost"] == "128.00"  # 1,6 kg × 80
    assert body["target_label"].startswith("Animal")


def test_consumed_cannot_exceed_distributed(ctx):
    response = ctx["client"].post(
        RECORDS,
        {
            "farm": ctx["farm"].pk,
            "animal": ctx["animal"].pk,
            "quantity_distributed_kg": "1",
            "quantity_consumed_kg": "1.2",
        },
        format="json",
    )
    assert response.status_code == 400


def test_group_record_requires_head_count(ctx):
    response = ctx["client"].post(
        RECORDS,
        {"farm": ctx["farm"].pk, "group": ctx["group"].pk, "quantity_distributed_kg": "10"},
        format="json",
    )
    assert response.status_code == 400 and "number_of_animals" in response.json()["errors"]


def test_summary_is_honest_about_missing_measurements(ctx):
    client, farm, animal = ctx["client"], ctx["farm"].pk, ctx["animal"].pk
    client.post(
        RECORDS,
        {"farm": farm, "animal": animal, "quantity_distributed_kg": "2", "quantity_consumed_kg": "1.8"},
        format="json",
    )
    client.post(RECORDS, {"farm": farm, "animal": animal, "quantity_distributed_kg": "2"}, format="json")
    body = client.get(f"{RECORDS}summary/").json()
    assert body["records"] == 2 and body["records_with_measured_consumption"] == 1
    assert Decimal(body["distributed_kg"]) == 4 and Decimal(body["consumed_kg"]) == Decimal("1.8")
    assert body["records_without_cost"] == 2


def test_feeding_records_are_isolated_and_exportable(ctx, make_user, client_for):
    ctx["client"].post(
        RECORDS,
        {"farm": ctx["farm"].pk, "animal": ctx["animal"].pk, "quantity_distributed_kg": "2"},
        format="json",
    )
    assert client_for(make_user()).get(RECORDS).json()["count"] == 0
    csv = ctx["client"].get(f"{RECORDS}export/").content.decode("utf-8-sig")
    assert csv.splitlines()[0].startswith("date;ration;animal") and len(csv.splitlines()) == 2


# --- Une estimation non vérifiée ne devient jamais une ration (décision du porteur de projet) ---------


@pytest.mark.parametrize(
    "mode, status, allowed",
    [
        ("ECONOMIC", "ESTIMATED", False),
        ("BALANCED", "PENDING_REVIEW", False),
        ("ECONOMIC", "REFUSED", False),
        ("ECONOMIC", "INFEASIBLE", False),
        ("ECONOMIC", "REJECTED", False),
        ("ECONOMIC", "VALIDATED", True),
        ("MANUAL", "DRAFT", True),
        ("MANUAL", "REJECTED", False),
    ],
)
def test_ration_requires_a_validated_engine_formula(ctx, ovin, mode, status, allowed):
    from django.utils import timezone

    formula = FeedFormula.objects.create(
        validated_at=timezone.now() if status == "VALIDATED" else None,
        farm=ctx["farm"],
        name=f"{mode} {status}",
        species=ovin,
        mode=mode,
        status=status,
    )
    response = ration(ctx, formula=formula.pk)
    assert (response.status_code == 201) is allowed, response.json()
    if not allowed:
        assert "formula" in response.json()["errors"]


def test_demo_farm_may_use_its_demo_estimate(client_for, breeder, make_farm, ovin):
    from animals.models import AnimalGroup

    demo = make_farm(owner=breeder, name="Démo", is_demo=True)
    formula = FeedFormula.objects.create(
        farm=demo, name="Démo", species=ovin, mode="ECONOMIC", status="ESTIMATED", is_demo=True
    )
    group = AnimalGroup.objects.create(farm=demo, name="Lot démo", is_demo=True)
    response = client_for(breeder).post(
        RATIONS,
        {"farm": demo.pk, "name": "Ration démo", "formula": formula.pk, "group": group.pk},
        format="json",
    )
    assert response.status_code == 201, response.json()


def test_feeding_record_label_is_readable():
    from datetime import date
    from decimal import Decimal

    from feeding.models import FeedingRecord

    record = FeedingRecord(fed_on=date(2026, 11, 7), quantity_distributed_kg=Decimal("10.000"))
    assert str(record) == "07/11/2026 — 10 kg"
