from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from alerts.engine import evaluate_farm
from animals.models import Animal, AnimalGroup
from feeding.models import FeedingRecord
from growth.models import Weighing

pytestmark = pytest.mark.django_db
URL = "/api/v1/dashboard/"


def test_empty_dashboard_reports_zeros_and_no_invented_values(client_for, breeder, farm):
    body = client_for(breeder).get(URL).json()
    assert body["animals"]["total"] == 0 and body["groups_count"] == 0
    assert body["weight_trend"]["points"] == []
    assert body["feeding_cost"]["estimated_cost"] is None and body["feeding_cost"]["records"] == 0


def test_dashboard_uses_real_data_of_accessible_farms_only(
    client_for, breeder, farm, ovin, make_farm, make_user
):
    today = timezone.localdate()
    a = Animal.objects.create(farm=farm, species=ovin, tag_number="D-1", sex="F")
    Animal.objects.create(farm=farm, species=ovin, tag_number="D-2", sex="M", status="SOLD")
    AnimalGroup.objects.create(farm=farm, name="Lot")
    Weighing.objects.create(animal=a, weight_kg=20, weighed_on=today - timedelta(days=40))
    Weighing.objects.create(animal=a, weight_kg=24, weighed_on=today)
    FeedingRecord.objects.create(
        farm=farm, animal=a, quantity_distributed_kg=2, estimated_cost=Decimal("150")
    )
    FeedingRecord.objects.create(farm=farm, animal=a, quantity_distributed_kg=1)
    other = make_farm(owner=make_user())
    Animal.objects.create(farm=other, species=ovin, tag_number="X", sex="F")
    evaluate_farm(farm)

    body = client_for(breeder).get(URL).json()
    assert body["animals"]["total"] == 1  # l'animal vendu et celui d'une autre ferme sont exclus
    assert body["animals"]["by_species"] == [{"code": "OVIN", "name": "Ovin", "count": 1}]
    assert body["groups_count"] == 1
    assert body["weighings"]["last_30_days"] == 1 and body["weighings"]["latest"][0]["weight_kg"] == "24.00"
    assert sum(p["weighings"] for p in body["weight_trend"]["points"]) == 2
    assert (
        body["feeding_cost"]["estimated_cost"] == "150.00"
        and body["feeding_cost"]["records_without_cost"] == 1
    )
    assert body["alerts"]["open"] >= 1
    assert any(item["label"] for item in body["recent_activity"]) or body["recent_activity"] == []


def test_alerts_can_be_filtered_by_animal(client_for, breeder, farm, ovin):
    a = Animal.objects.create(farm=farm, species=ovin, tag_number="F-1", sex="F")
    Animal.objects.create(farm=farm, species=ovin, tag_number="F-2", sex="F")
    evaluate_farm(farm)
    results = client_for(breeder).get("/api/v1/alerts/", {"animal": a.pk}).json()["results"]
    assert results and all(r["target"] == {"type": "animal", "id": a.pk} for r in results)
