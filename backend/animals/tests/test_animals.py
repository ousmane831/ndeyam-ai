from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from animals.models import Animal, AnimalGroup, Breed, Species
from conftest import rejected_by_database

pytestmark = pytest.mark.django_db


def test_seeded_species_ovine_active_others_ready_but_inactive():
    assert Species.objects.get(code="OVIN").is_active
    assert not Species.objects.get(code="CAPRIN").is_active
    assert not Species.objects.get(code="BOVIN").is_active


def test_seeded_ovine_nomenclatures(ovin):
    assert {"Peul-Peul", "Touabire", "Ladoum", "Djallonké", "Waralé"} <= set(
        ovin.breeds.values_list("name", flat=True)
    )
    assert ovin.categories.filter(code="BREBIS").exists()
    assert ovin.stages.filter(code="LACTATION").exists()


def test_tag_number_unique_within_a_farm_only(farm, make_farm, ovin):
    Animal.objects.create(farm=farm, species=ovin, tag_number="T1", sex="F")
    Animal.objects.create(farm=make_farm(), species=ovin, tag_number="T1", sex="F")
    with rejected_by_database():
        Animal.objects.create(farm=farm, species=ovin, tag_number="T1", sex="M")


def test_initial_weight_must_be_positive(farm, ovin):
    with rejected_by_database():
        Animal.objects.create(farm=farm, species=ovin, tag_number="T2", sex="M", initial_weight_kg=0)


def test_breed_must_belong_to_species(farm, ovin):
    caprin = Species.objects.get(code="CAPRIN")
    goat_breed = Breed.objects.create(species=caprin, name="Race caprine test")
    animal = Animal(farm=farm, species=ovin, tag_number="T3", sex="M", breed=goat_breed)
    with pytest.raises(ValidationError) as exc:
        animal.full_clean()
    assert "breed" in exc.value.message_dict


def test_group_must_belong_to_same_farm(farm, make_farm, ovin):
    other_group = AnimalGroup.objects.create(farm=make_farm(), name="Lot étranger")
    animal = Animal(farm=farm, species=ovin, tag_number="T4", sex="F", group=other_group)
    with pytest.raises(ValidationError) as exc:
        animal.full_clean()
    assert "group" in exc.value.message_dict


def test_birth_date_cannot_be_in_the_future(farm, ovin):
    animal = Animal(
        farm=farm, species=ovin, tag_number="T5", sex="F", birth_date=timezone.localdate() + timedelta(days=1)
    )
    with pytest.raises(ValidationError):
        animal.full_clean()


def test_age_in_days(farm, ovin):
    today = timezone.localdate()
    animal = Animal(farm=farm, species=ovin, tag_number="T6", sex="F", birth_date=today - timedelta(days=90))
    assert animal.age_in_days(today) == 90
    assert Animal(farm=farm, species=ovin, tag_number="T7", sex="F").age_in_days() is None


def test_each_animal_gets_a_unique_uuid(farm, ovin):
    a = Animal.objects.create(farm=farm, species=ovin, tag_number="U1", sex="F")
    b = Animal.objects.create(farm=farm, species=ovin, tag_number="U2", sex="F")
    assert a.uuid != b.uuid
