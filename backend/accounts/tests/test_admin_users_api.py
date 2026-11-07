import pytest

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/users/"


@pytest.fixture
def admin_user(make_user):
    return make_user("ADMIN")


@pytest.mark.parametrize("role", ["ELEVEUR", "EXPERT"])
def test_non_admins_cannot_manage_users(client_for, make_user, role):
    client = client_for(make_user(role))
    assert client.get(URL).status_code == 403
    assert (
        client.post(URL, {"email": "x@y.sn", "password": "Mot-De-Passe-2026", "role": "ADMIN"}).status_code
        == 403
    )


def test_admin_lists_filters_and_searches_users(client_for, admin_user, make_user):
    make_user("EXPERT", email="expert@isra.sn")
    make_user("ELEVEUR", email="eleveur@ferme.sn")
    client = client_for(admin_user)
    assert client.get(URL).json()["count"] == 3
    experts = client.get(URL, {"role": "EXPERT"}).json()
    assert [u["email"] for u in experts["results"]] == ["expert@isra.sn"]
    assert client.get(URL, {"search": "ferme"}).json()["count"] == 1


def test_admin_creates_an_expert(client_for, admin_user, django_user_model):
    response = client_for(admin_user).post(
        URL,
        {
            "email": "Expert@ISRA.sn",
            "password": "Mot-De-Passe-2026",
            "role": "EXPERT",
            "first_name": "Moussa",
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    user = django_user_model.objects.get(email="expert@isra.sn")
    assert user.role == "EXPERT" and user.check_password("Mot-De-Passe-2026")
    assert "password" not in response.json()


def test_admin_can_deactivate_and_change_role(client_for, admin_user, make_user):
    target = make_user()
    response = client_for(admin_user).patch(
        f"{URL}{target.pk}/", {"is_active": False, "role": "EXPERT"}, format="json"
    )
    assert response.status_code == 200
    target.refresh_from_db()
    assert not target.is_active and target.role == "EXPERT"


def test_promoting_to_admin_grants_django_admin_access(client_for, admin_user, make_user):
    target = make_user()
    client_for(admin_user).patch(f"{URL}{target.pk}/", {"role": "ADMIN"}, format="json")
    target.refresh_from_db()
    assert target.is_staff


def test_admin_cannot_lock_himself_out(client_for, admin_user):
    client = client_for(admin_user)
    assert client.patch(f"{URL}{admin_user.pk}/", {"is_active": False}, format="json").status_code == 400
    assert client.patch(f"{URL}{admin_user.pk}/", {"role": "ELEVEUR"}, format="json").status_code == 400


def test_users_cannot_be_deleted_only_deactivated(client_for, admin_user, make_user):
    assert client_for(admin_user).delete(f"{URL}{make_user().pk}/").status_code == 405
