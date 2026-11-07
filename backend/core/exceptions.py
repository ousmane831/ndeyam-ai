"""
Gestionnaire d'erreurs centralisé de l'API.

Toutes les erreurs renvoyées par l'API suivent le même format, ce qui permet
au frontend de les afficher de manière uniforme :

    {
        "detail": "Message lisible en français",
        "code": "code_machine",
        "errors": {"champ": ["message", ...]}   # uniquement pour les erreurs de validation
    }
"""

import logging

from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError, RestrictedError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    # Suppression impossible : l'objet est encore utilisé par d'autres données (on_delete=PROTECT).
    if isinstance(exc, ProtectedError | RestrictedError):
        used_by = (
            sorted({obj._meta.verbose_name_plural for obj in list(exc.protected_objects)[:50]})
            if isinstance(exc, ProtectedError)
            else []
        )
        detail = "Suppression impossible : cet élément est encore utilisé"
        detail += f" ({', '.join(used_by)})." if used_by else "."
        return Response({"detail": detail, "code": "protected"}, status=status.HTTP_409_CONFLICT)

    # Conversion des exceptions Django natives en exceptions DRF.
    if isinstance(exc, Http404):
        exc = exceptions.NotFound("Ressource introuvable.")
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = exception_handler(exc, context)

    if response is None:
        # Erreur inattendue : on la journalise sans exposer de détails internes.
        logger.exception("Erreur non gérée dans l'API", exc_info=exc)
        return Response(
            {"detail": "Une erreur interne est survenue.", "code": "server_error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, exceptions.ValidationError):
        errors = response.data
        if isinstance(errors, list):
            errors = {"non_field_errors": errors}
        response.data = {
            "detail": "Les données envoyées sont invalides.",
            "code": "validation_error",
            "errors": errors,
        }
        return response

    detail = response.data.get("detail") if isinstance(response.data, dict) else None
    code = getattr(getattr(exc, "detail", None), "code", None) or getattr(exc, "default_code", "error")
    response.data = {"detail": str(detail) if detail else str(exc), "code": code}
    return response
