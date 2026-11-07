import pytest

pytestmark = pytest.mark.django_db


def test_validation_history_hidden_from_breeders(client_for, breeder, expert):
    assert client_for(breeder).get("/api/v1/validation-records/").status_code == 403
    assert client_for(expert).get("/api/v1/validation-records/").status_code == 200


def test_activity_log_reserved_to_admins(client_for, breeder, expert, make_user):
    assert client_for(breeder).get("/api/v1/activity-logs/").status_code == 403
    assert client_for(expert).get("/api/v1/activity-logs/").status_code == 403
    assert client_for(make_user("ADMIN")).get("/api/v1/activity-logs/").status_code == 200


def test_import_history_shows_only_own_imports(client_for, breeder, make_user):
    from governance.models import ImportBatch

    ImportBatch.objects.create(kind="animals", file_name="a.csv", imported_by=breeder)
    ImportBatch.objects.create(kind="animals", file_name="b.csv", imported_by=make_user())
    assert client_for(breeder).get("/api/v1/import-batches/").json()["count"] == 1
    assert client_for(make_user("ADMIN")).get("/api/v1/import-batches/").json()["count"] == 2
