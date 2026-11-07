import re

import pytest
from django.core import mail

from farms.models import FarmMembership
from governance.models import ActivityLog

pytestmark = pytest.mark.django_db

STRONG = "Brebis-Touabire-2026"

REGISTER = "/api/v1/auth/register/"
LOGIN = "/api/v1/auth/login/"
REFRESH = "/api/v1/auth/refresh/"
LOGOUT = "/api/v1/auth/logout/"
ME = "/api/v1/auth/me/"
CHANGE_PASSWORD = "/api/v1/auth/change-password/"
RESET = "/api/v1/auth/password-reset/"
RESET_CONFIRM = "/api/v1/auth/password-reset/confirm/"


def register_payload(**overrides):
    return {
        "email": "Awa.Ndiaye@Exemple.SN",
        "password": STRONG,
        "password_confirm": STRONG,
        "first_name": "Awa",
        "last_name": "Ndiaye",
        "phone": "+221 77 000 00 00",
        "farm_name": "Bergerie de Kaolack",
        "farm_region": "Kaolack",
        **overrides,
    }


def login(api, email, password=STRONG):
    return api.post(LOGIN, {"email": email, "password": password}, format="json")


# --- Inscription ------------------------------------------------------------------------


def test_register_creates_breeder_farm_and_owner_membership(api):
    response = api.post(REGISTER, register_payload(), format="json")
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["user"]["email"] == "awa.ndiaye@exemple.sn"
    assert body["user"]["role"] == "ELEVEUR"
    assert body["access"] and body["refresh"]
    membership = FarmMembership.objects.get(user__email="awa.ndiaye@exemple.sn")
    assert membership.role == "OWNER" and membership.farm.name == "Bergerie de Kaolack"
    assert body["user"]["memberships"][0]["farm_name"] == "Bergerie de Kaolack"
    assert ActivityLog.objects.filter(action="account.registered").exists()


def test_register_cannot_choose_a_privileged_role(api):
    response = api.post(REGISTER, register_payload(role="ADMIN"), format="json")
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "ELEVEUR"


def test_register_rejects_duplicate_email_case_insensitive(api, make_user):
    make_user(email="awa.ndiaye@exemple.sn")
    response = api.post(REGISTER, register_payload(), format="json")
    assert response.status_code == 400
    assert "email" in response.json()["errors"]


def test_register_rejects_weak_password(api):
    response = api.post(REGISTER, register_payload(password="1234", password_confirm="1234"), format="json")
    assert response.status_code == 400
    assert "password" in response.json()["errors"]


def test_register_rejects_mismatched_passwords(api):
    response = api.post(REGISTER, register_payload(password_confirm="Autre-Mot-2026!"), format="json")
    assert response.status_code == 400
    assert "password_confirm" in response.json()["errors"]


def test_register_requires_a_farm_name(api):
    payload = register_payload()
    del payload["farm_name"]
    response = api.post(REGISTER, payload, format="json")
    assert response.status_code == 400
    assert "farm_name" in response.json()["errors"]


def test_failed_registration_creates_nothing(api, django_user_model):
    api.post(REGISTER, register_payload(password_confirm="x"), format="json")
    assert not django_user_model.objects.exists()


# --- Connexion / jetons ---------------------------------------------------------------


@pytest.fixture
def awa(make_user):
    user = make_user(email="awa@exemple.sn")
    user.set_password(STRONG)
    user.save()
    return user


def test_login_returns_tokens_and_profile(api, awa):
    response = login(api, "AWA@exemple.sn")
    assert response.status_code == 200
    assert {"access", "refresh", "user"} <= response.json().keys()
    assert response.json()["user"]["email"] == "awa@exemple.sn"


def test_login_with_wrong_password_gives_generic_french_error(api, awa):
    response = login(api, "awa@exemple.sn", "mauvais")
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"]


def test_unknown_email_gets_same_error_as_wrong_password(api, awa):
    assert login(api, "inconnu@exemple.sn").json() == login(api, "awa@exemple.sn", "mauvais").json()


def test_inactive_user_cannot_login(api, awa):
    awa.is_active = False
    awa.save()
    assert login(api, "awa@exemple.sn").status_code == 401


def test_protected_endpoint_requires_token(api):
    response = api.get(ME)
    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_access_token_grants_access(api, awa):
    access = login(api, "awa@exemple.sn").json()["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert api.get(ME).json()["email"] == "awa@exemple.sn"


def test_invalid_token_is_rejected(api):
    api.credentials(HTTP_AUTHORIZATION="Bearer abc.def.ghi")
    assert api.get(ME).status_code == 401


def test_refresh_rotates_and_revokes_previous_token(api, awa):
    refresh = login(api, "awa@exemple.sn").json()["refresh"]
    first = api.post(REFRESH, {"refresh": refresh}, format="json")
    assert first.status_code == 200
    assert first.json()["refresh"] != refresh
    # L'ancien jeton de rafraîchissement ne peut plus servir.
    assert api.post(REFRESH, {"refresh": refresh}, format="json").status_code == 401


def test_refresh_refused_for_deactivated_user(api, awa):
    refresh = login(api, "awa@exemple.sn").json()["refresh"]
    awa.is_active = False
    awa.save()
    assert api.post(REFRESH, {"refresh": refresh}, format="json").status_code == 401


def test_logout_revokes_refresh_token(api, awa):
    tokens = login(api, "awa@exemple.sn").json()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert api.post(LOGOUT, {"refresh": tokens["refresh"]}, format="json").status_code == 205
    assert api.post(REFRESH, {"refresh": tokens["refresh"]}, format="json").status_code == 401


def test_cannot_logout_someone_else(api, awa, make_user, client_for):
    other_refresh = login(api, "awa@exemple.sn").json()["refresh"]
    response = client_for(make_user()).post(LOGOUT, {"refresh": other_refresh}, format="json")
    assert response.status_code == 400
    assert api.post(REFRESH, {"refresh": other_refresh}, format="json").status_code == 200


# --- Profil ------------------------------------------------------------------------------


def test_profile_update_cannot_change_role_or_email(client_for, awa):
    client = client_for(awa)
    response = client.patch(
        ME, {"first_name": "Aïssatou", "role": "ADMIN", "email": "pirate@x.sn"}, format="json"
    )
    assert response.status_code == 200
    awa.refresh_from_db()
    assert awa.first_name == "Aïssatou"
    assert awa.role == "ELEVEUR" and awa.email == "awa@exemple.sn"


# --- Mot de passe -------------------------------------------------------------------------


def test_change_password_requires_current_password(client_for, awa):
    response = client_for(awa).post(
        CHANGE_PASSWORD, {"current_password": "faux", "new_password": "Nouveau-Mot-2026"}, format="json"
    )
    assert response.status_code == 400
    assert "current_password" in response.json()["errors"]


def test_change_password_revokes_existing_sessions(api, client_for, awa):
    refresh = login(api, "awa@exemple.sn").json()["refresh"]
    response = client_for(awa).post(
        CHANGE_PASSWORD, {"current_password": STRONG, "new_password": "Nouveau-Mot-2026"}, format="json"
    )
    assert response.status_code == 200
    assert api.post(REFRESH, {"refresh": refresh}, format="json").status_code == 401
    assert login(api, "awa@exemple.sn", "Nouveau-Mot-2026").status_code == 200


def reset_link_params():
    body = mail.outbox[-1].body
    uid = re.search(r"uid=([\w-]+)", body).group(1)
    token = re.search(r"token=([\w-]+)", body).group(1)
    return uid, token


def test_password_reset_full_flow(api, awa):
    response = api.post(RESET, {"email": "awa@exemple.sn"}, format="json")
    assert response.status_code == 200
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["awa@exemple.sn"]
    assert "/reinitialiser-mot-de-passe?uid=" in mail.outbox[0].body
    uid, token = reset_link_params()
    confirm = api.post(
        RESET_CONFIRM, {"uid": uid, "token": token, "new_password": "Nouveau-Mot-2026"}, format="json"
    )
    assert confirm.status_code == 200
    assert login(api, "awa@exemple.sn", "Nouveau-Mot-2026").status_code == 200


def test_password_reset_link_is_single_use(api, awa):
    api.post(RESET, {"email": "awa@exemple.sn"}, format="json")
    uid, token = reset_link_params()
    payload = {"uid": uid, "token": token, "new_password": "Nouveau-Mot-2026"}
    assert api.post(RESET_CONFIRM, payload, format="json").status_code == 200
    second = api.post(RESET_CONFIRM, {**payload, "new_password": "Encore-Autre-2026"}, format="json")
    assert second.status_code == 400
    assert second.json()["code"] == "invalid_reset_link"


def test_password_reset_does_not_reveal_unknown_accounts(api, awa):
    known = api.post(RESET, {"email": "awa@exemple.sn"}, format="json")
    unknown = api.post(RESET, {"email": "personne@exemple.sn"}, format="json")
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(mail.outbox) == 1


def test_password_reset_rejects_forged_token(api, awa):
    api.post(RESET, {"email": "awa@exemple.sn"}, format="json")
    uid, _ = reset_link_params()
    response = api.post(
        RESET_CONFIRM, {"uid": uid, "token": "faux-jeton", "new_password": "Nouveau-Mot-2026"}, format="json"
    )
    assert response.status_code == 400


def test_password_reset_still_enforces_password_strength(api, awa):
    api.post(RESET, {"email": "awa@exemple.sn"}, format="json")
    uid, token = reset_link_params()
    response = api.post(RESET_CONFIRM, {"uid": uid, "token": token, "new_password": "123"}, format="json")
    assert response.status_code == 400
    assert "new_password" in response.json()["errors"]
