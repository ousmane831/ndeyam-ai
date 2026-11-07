from django.http import Http404
from rest_framework import exceptions

from core.exceptions import api_exception_handler


def test_validation_error_is_normalised():
    response = api_exception_handler(exceptions.ValidationError({"poids": ["Doit être positif."]}), {})
    assert response.status_code == 400
    assert response.data == {
        "detail": "Les données envoyées sont invalides.",
        "code": "validation_error",
        "errors": {"poids": ["Doit être positif."]},
    }


def test_django_404_is_normalised():
    response = api_exception_handler(Http404(), {})
    assert response.status_code == 404
    assert response.data["code"] == "not_found"


def test_unexpected_error_hides_internal_details():
    response = api_exception_handler(RuntimeError("secret interne"), {})
    assert response.status_code == 500
    assert "secret interne" not in str(response.data)
    assert response.data["code"] == "server_error"
