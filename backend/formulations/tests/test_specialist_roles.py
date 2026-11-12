"""Rôles des spécialistes invités : chacun agit dans son domaine, le reste en lecture seule."""

import pytest
from django.utils import timezone

from farms.models import FarmMembership

from .test_formula_api import URL, create, setup  # noqa: F401  (fixture réutilisée)

pytestmark = pytest.mark.django_db


@pytest.fixture
def team(setup, animal, make_user, client_for):  # noqa: F811
    farm = setup["farm"]
    nutritionist = make_user("EXPERT", email="nutrition@isra.sn")
    vet = make_user("EXPERT", email="veto@isra.sn")
    technician = make_user(email="technicien@ferme.sn")
    for user, role in ((nutritionist, "EXPERT"), (vet, "VETERINARIAN"), (technician, "TECHNICIAN")):
        FarmMembership.objects.create(farm=farm, user=user, role=role)
    return {
        "nutritionist": client_for(nutritionist),
        "vet": client_for(vet),
        "technician": client_for(technician),
        "animal": animal,
        "farm": farm,
    }


def weigh(client, animal, kg="30"):
    data = {
        "animal": animal.pk,
        "weight_kg": kg,
        "weighed_on": timezone.localdate().isoformat(),
        "method": "SCALE",
    }
    return client.post("/api/v1/weighings/", data, format="json")


def observe(client, animal):
    return client.post(
        f"/api/v1/animals/{animal.pk}/observations/",
        {"kind": "HEALTH", "text": "Boiterie légère."},
        format="json",
    )


def test_only_the_nutritionist_validates_rations(setup, team):  # noqa: F811
    formula_id = create(setup).json()["id"]
    setup["client"].post(f"{URL}{formula_id}/submit-review/")
    for who in ("vet", "technician"):
        assert team[who].post(f"{URL}{formula_id}/validate/").status_code == 403, who
    response = team["nutritionist"].post(
        f"{URL}{formula_id}/validate/", {"comment": "Vérifiée"}, format="json"
    )
    assert response.status_code == 200 and response.json()["status"] == "VALIDATED"


def test_technician_weighs_but_does_not_manage_the_farm(team):
    animal = team["animal"]
    assert weigh(team["technician"], animal).status_code == 201
    session = {
        "weighed_on": "2026-11-01",
        "method": "SCALE",
        "entries": [{"animal": animal.pk, "weight_kg": "31"}],
    }
    assert team["technician"].post("/api/v1/weighings/bulk/", session, format="json").status_code == 201
    assert observe(team["technician"], animal).status_code == 201
    assert (
        team["technician"].patch(f"/api/v1/animals/{animal.pk}/", {"name": "X"}, format="json").status_code
        == 403
    )


def test_vet_records_health_observations_but_not_weighings(team):
    animal = team["animal"]
    assert observe(team["vet"], animal).status_code == 201
    assert weigh(team["vet"], animal).status_code == 403
    assert weigh(team["nutritionist"], animal).status_code == 403
    assert observe(team["nutritionist"], animal).status_code == 403


def test_invitation_rules_by_account_type(setup, make_user):  # noqa: F811
    farm, owner = setup["farm"], setup["client"]
    breeder_account = make_user(email="tech2@ferme.sn")
    expert_account = make_user("EXPERT", email="expert2@isra.sn")
    url = f"/api/v1/farms/{farm.pk}/members/"
    vet_by_breeder = owner.post(url, {"email": breeder_account.email, "role": "VETERINARIAN"}, format="json")
    assert vet_by_breeder.status_code == 400
    tech = owner.post(url, {"email": breeder_account.email, "role": "TECHNICIAN"}, format="json")
    assert tech.status_code == 201
    assert tech.json()["role_label"] == "Technicien d'élevage (pesées, suivi)"
    assert (
        owner.post(url, {"email": expert_account.email, "role": "VETERINARIAN"}, format="json").status_code
        == 201
    )
