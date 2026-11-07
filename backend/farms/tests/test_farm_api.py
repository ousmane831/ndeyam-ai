"""Isolation des exploitations et permissions par rôle, vérifiées via l'API."""

import pytest

from farms.models import FarmMembership

pytestmark = pytest.mark.django_db

FARMS = "/api/v1/farms/"


def members_url(farm):
    return f"{FARMS}{farm.pk}/members/"


@pytest.fixture
def setup(make_user, make_farm):
    alice, bob = make_user(email="alice@ferme.sn"), make_user(email="bob@ferme.sn")
    return {
        "alice": alice,
        "bob": bob,
        "farm_a": make_farm(owner=alice, name="Ferme d'Alice"),
        "farm_b": make_farm(owner=bob, name="Ferme de Bob"),
    }


# --- Isolation entre éleveurs -----------------------------------------------------------


def test_breeder_lists_only_his_farms(client_for, setup):
    body = client_for(setup["alice"]).get(FARMS).json()
    assert [f["name"] for f in body["results"]] == ["Ferme d'Alice"]
    assert body["results"][0]["my_role"] == "OWNER"


def test_breeder_cannot_read_another_farm(client_for, setup):
    assert client_for(setup["alice"]).get(f"{FARMS}{setup['farm_b'].pk}/").status_code == 404


def test_breeder_cannot_modify_another_farm(client_for, setup):
    response = client_for(setup["alice"]).patch(
        f"{FARMS}{setup['farm_b'].pk}/", {"name": "Piratée"}, format="json"
    )
    assert response.status_code == 404
    setup["farm_b"].refresh_from_db()
    assert setup["farm_b"].name == "Ferme de Bob"


def test_breeder_cannot_see_or_add_members_of_another_farm(client_for, setup, make_user):
    client = client_for(setup["alice"])
    assert client.get(members_url(setup["farm_b"])).status_code == 404
    response = client.post(
        members_url(setup["farm_b"]), {"email": "alice@ferme.sn", "role": "MANAGER"}, format="json"
    )
    assert response.status_code == 404
    assert not FarmMembership.objects.filter(farm=setup["farm_b"], user=setup["alice"]).exists()


def test_anonymous_has_no_access(api, setup):
    assert api.get(FARMS).status_code == 401
    assert api.get(f"{FARMS}{setup['farm_a'].pk}/").status_code == 401


def test_farms_cannot_be_deleted(client_for, setup):
    assert client_for(setup["alice"]).delete(f"{FARMS}{setup['farm_a'].pk}/").status_code == 405


# --- Rôles dans l'exploitation ----------------------------------------------------------


def test_owner_updates_his_farm(client_for, setup):
    response = client_for(setup["alice"]).patch(
        f"{FARMS}{setup['farm_a'].pk}/", {"region": "Thiès"}, format="json"
    )
    assert response.status_code == 200 and response.json()["region"] == "Thiès"


def test_manager_can_write_but_not_manage_members(client_for, setup, make_user):
    manager = make_user()
    FarmMembership.objects.create(farm=setup["farm_a"], user=manager, role="MANAGER")
    client = client_for(manager)
    assert (
        client.patch(f"{FARMS}{setup['farm_a'].pk}/", {"locality": "Mbour"}, format="json").status_code == 200
    )
    response = client.post(
        members_url(setup["farm_a"]), {"email": "bob@ferme.sn", "role": "MANAGER"}, format="json"
    )
    assert response.status_code == 403


def test_invited_expert_reads_but_cannot_write(client_for, setup, make_user):
    expert = make_user("EXPERT")
    FarmMembership.objects.create(farm=setup["farm_a"], user=expert, role="EXPERT")
    client = client_for(expert)
    assert client.get(f"{FARMS}{setup['farm_a'].pk}/").status_code == 200
    assert client.get(members_url(setup["farm_a"])).status_code == 200
    assert (
        client.patch(f"{FARMS}{setup['farm_a'].pk}/", {"name": "Modifiée"}, format="json").status_code == 403
    )
    assert client.get(f"{FARMS}{setup['farm_b'].pk}/").status_code == 404


def test_expert_cannot_create_a_farm(client_for, make_user):
    response = client_for(make_user("EXPERT")).post(FARMS, {"name": "Ferme expert"}, format="json")
    assert response.status_code == 403


def test_breeder_creates_a_second_farm_and_becomes_owner(client_for, setup):
    response = client_for(setup["alice"]).post(
        FARMS, {"name": "Seconde ferme", "region": "Louga"}, format="json"
    )
    assert response.status_code == 201
    assert response.json()["my_role"] == "OWNER"
    assert FarmMembership.objects.get(farm_id=response.json()["id"]).user == setup["alice"]


def test_platform_admin_sees_every_farm(client_for, setup, make_user):
    assert client_for(make_user("ADMIN")).get(FARMS).json()["count"] == 2


def test_country_code_is_validated(client_for, setup):
    response = client_for(setup["alice"]).patch(
        f"{FARMS}{setup['farm_a'].pk}/", {"country": "Senegal"}, format="json"
    )
    assert response.status_code == 400


# --- Gestion des membres ------------------------------------------------------------------


def test_owner_invites_an_expert_who_then_gains_read_access(client_for, setup, make_user):
    expert = make_user("EXPERT", email="expert@isra.sn")
    response = client_for(setup["alice"]).post(
        members_url(setup["farm_a"]), {"email": "EXPERT@isra.sn", "role": "EXPERT"}, format="json"
    )
    assert response.status_code == 201, response.json()
    assert client_for(expert).get(f"{FARMS}{setup['farm_a'].pk}/").status_code == 200


def test_only_expert_accounts_can_be_invited_as_experts(client_for, setup):
    response = client_for(setup["alice"]).post(
        members_url(setup["farm_a"]), {"email": "bob@ferme.sn", "role": "EXPERT"}, format="json"
    )
    assert response.status_code == 400


def test_expert_account_cannot_be_given_write_access(client_for, setup, make_user):
    make_user("EXPERT", email="expert@isra.sn")
    response = client_for(setup["alice"]).post(
        members_url(setup["farm_a"]), {"email": "expert@isra.sn", "role": "MANAGER"}, format="json"
    )
    assert response.status_code == 400


def test_owner_role_cannot_be_granted(client_for, setup):
    response = client_for(setup["alice"]).post(
        members_url(setup["farm_a"]), {"email": "bob@ferme.sn", "role": "OWNER"}, format="json"
    )
    assert response.status_code == 400


def test_inviting_unknown_email_fails_explicitly(client_for, setup):
    response = client_for(setup["alice"]).post(
        members_url(setup["farm_a"]), {"email": "inconnu@ferme.sn", "role": "MANAGER"}, format="json"
    )
    assert response.status_code == 400
    assert "email" in response.json()["errors"]


def test_owner_cannot_be_removed(client_for, setup):
    owner_membership = FarmMembership.objects.get(farm=setup["farm_a"], role="OWNER")
    response = client_for(setup["alice"]).delete(f"{members_url(setup['farm_a'])}{owner_membership.pk}/")
    assert response.status_code == 403


def test_removed_member_loses_access(client_for, setup, make_user):
    manager = make_user()
    membership = FarmMembership.objects.create(farm=setup["farm_a"], user=manager, role="MANAGER")
    assert (
        client_for(setup["alice"]).delete(f"{members_url(setup['farm_a'])}{membership.pk}/").status_code
        == 204
    )
    assert client_for(manager).get(f"{FARMS}{setup['farm_a'].pk}/").status_code == 404


def test_member_actions_are_logged(client_for, setup, make_user):
    from governance.models import ActivityLog

    make_user("EXPERT", email="expert@isra.sn")
    client_for(setup["alice"]).post(
        members_url(setup["farm_a"]), {"email": "expert@isra.sn", "role": "EXPERT"}, format="json"
    )
    log = ActivityLog.objects.get(action="farm.member_added")
    assert log.farm == setup["farm_a"] and log.details["user"] == "expert@isra.sn"
