"""Chaque page d'administration (liste + ajout) doit s'afficher sans erreur pour un administrateur."""

import pytest
from django.contrib import admin
from django.urls import reverse

pytestmark = pytest.mark.django_db

MODEL_ADMINS = sorted(admin.site._registry.items(), key=lambda item: item[0]._meta.label)


@pytest.fixture
def admin_client_logged(client, django_user_model):
    user = django_user_model.objects.create_superuser(email="admin@test.sn", password="MotDePasse-Admin-2026")
    client.force_login(user)
    return client


@pytest.mark.parametrize("model", [m for m, _ in MODEL_ADMINS], ids=lambda m: m._meta.label)
def test_admin_changelist_renders(admin_client_logged, model):
    url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
    assert admin_client_logged.get(url).status_code == 200


READ_ONLY_HISTORIES = {
    "governance.ValidationRecord",
    "governance.ImportBatch",
    "governance.ActivityLog",
    "token_blacklist.OutstandingToken",  # géré par SimpleJWT
}


@pytest.mark.parametrize("model", [m for m, _ in MODEL_ADMINS], ids=lambda m: m._meta.label)
def test_admin_add_form_renders(admin_client_logged, model):
    url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_add")
    response = admin_client_logged.get(url)
    # Les historiques sont en lecture seule : l'ajout manuel y est volontairement interdit.
    expected = 403 if model._meta.label in READ_ONLY_HISTORIES else 200
    assert response.status_code == expected
