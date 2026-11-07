import pytest
from django.test import override_settings
from rest_framework.test import APIClient


def llm_settings(provider, api_key="", base_url=""):
    return {
        "PROVIDER": provider,
        "MODEL": "m",
        "API_KEY": api_key,
        "BASE_URL": base_url,
        "TIMEOUT_SECONDS": 5,
    }


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_health_reports_real_database_connection(client):
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"]["connected"] is True
    assert body["database"]["engine"].startswith("PostgreSQL")


@pytest.mark.django_db
def test_health_reports_assistant_not_configured_without_key(client):
    body = client.get("/api/v1/health/").json()
    assert body["assistant"] == {"configured": False, "provider": None}


@pytest.mark.django_db
@override_settings(LLM=llm_settings("anthropic"))
def test_health_requires_api_key_for_cloud_provider(client):
    body = client.get("/api/v1/health/").json()
    assert body["assistant"]["configured"] is False


@pytest.mark.django_db
@override_settings(LLM=llm_settings("ollama", base_url="http://localhost:11434"))
def test_health_ollama_needs_no_key(client):
    body = client.get("/api/v1/health/").json()
    assert body["assistant"] == {"configured": True, "provider": "ollama"}


@pytest.mark.django_db
def test_health_never_exposes_secrets(client):
    raw = client.get("/api/v1/health/").content.decode()
    assert "API_KEY" not in raw and "PASSWORD" not in raw


def test_openapi_schema_is_served(client, db):
    response = client.get("/api/schema/")
    assert response.status_code == 200
    assert b"NDEYAM AI" in response.content


@pytest.mark.django_db
def test_unknown_route_returns_404(client):
    assert client.get("/api/v1/route-inexistante/").status_code == 404
