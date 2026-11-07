from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from conftest import rejected_by_database
from growth.models import GrowthMonitoringRange, Weighing

pytestmark = pytest.mark.django_db


def test_weight_must_be_positive(animal):
    with rejected_by_database():
        Weighing.objects.create(animal=animal, weight_kg=0)


def test_one_weighing_per_animal_per_day(animal):
    Weighing.objects.create(animal=animal, weight_kg=25)
    with rejected_by_database():
        Weighing.objects.create(animal=animal, weight_kg=26)


def test_weighing_cannot_be_in_the_future(animal):
    weighing = Weighing(animal=animal, weight_kg=25, weighed_on=timezone.localdate() + timedelta(days=1))
    with pytest.raises(ValidationError):
        weighing.full_clean()


def test_weighing_cannot_precede_birth(animal):
    animal.birth_date = timezone.localdate() - timedelta(days=10)
    animal.save()
    weighing = Weighing(animal=animal, weight_kg=5, weighed_on=timezone.localdate() - timedelta(days=20))
    with pytest.raises(ValidationError):
        weighing.full_clean()


def test_growth_range_needs_a_bound_and_ordered_values(ovin):
    with rejected_by_database():
        GrowthMonitoringRange.objects.create(name="Vide", species=ovin)
    with rejected_by_database():
        GrowthMonitoringRange.objects.create(name="Inversée", species=ovin, adg_min_g=200, adg_max_g=100)


def test_demo_growth_range_cannot_be_validated(ovin, validated_kwargs):
    with rejected_by_database():
        GrowthMonitoringRange.objects.create(
            name="Démo", species=ovin, adg_min_g=50, is_demo=True, **validated_kwargs
        )
