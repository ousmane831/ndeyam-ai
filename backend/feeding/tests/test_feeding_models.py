from datetime import timedelta

import pytest
from django.utils import timezone

from animals.models import AnimalGroup
from conftest import rejected_by_database
from feeding.models import FeedingRecord, Ration
from formulations.models import FeedFormula

pytestmark = pytest.mark.django_db


@pytest.fixture
def formula(farm, ovin):
    return FeedFormula.objects.create(farm=farm, name="F", species=ovin, mode="MANUAL")


def test_ration_targets_an_animal_or_a_group_not_both(farm, formula, animal):
    group = AnimalGroup.objects.create(farm=farm, name="Lot 1")
    with rejected_by_database():
        Ration.objects.create(farm=farm, name="R", formula=formula, animal=animal, group=group)
    with rejected_by_database():
        Ration.objects.create(farm=farm, name="R", formula=formula)


def test_ration_end_date_after_start(farm, formula, animal):
    today = timezone.localdate()
    with rejected_by_database():
        Ration.objects.create(
            farm=farm,
            name="R",
            formula=formula,
            animal=animal,
            start_date=today,
            end_date=today - timedelta(days=1),
        )


def test_consumed_quantity_is_optional_and_never_assumed(farm, animal):
    record = FeedingRecord.objects.create(farm=farm, animal=animal, quantity_distributed_kg=2)
    assert record.quantity_consumed_kg is None


def test_consumed_cannot_exceed_distributed(farm, animal):
    with rejected_by_database():
        FeedingRecord.objects.create(
            farm=farm, animal=animal, quantity_distributed_kg=2, quantity_consumed_kg=3
        )


def test_quantities_cannot_be_negative(farm, animal):
    with rejected_by_database():
        FeedingRecord.objects.create(farm=farm, animal=animal, quantity_distributed_kg=-1)
