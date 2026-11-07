import logging

from django.conf import settings
from django.db import connection
from django.db.utils import DatabaseError
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthView(APIView):
    """
    État réel de la plateforme : la connexion PostgreSQL est vérifiée par une requête,
    et l'on indique si l'assistant IA est configuré (sans jamais exposer la clé).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="État de santé de l'API",
        responses=inline_serializer(
            name="HealthResponse",
            fields={
                "status": serializers.CharField(),
                "app": serializers.CharField(),
                "version": serializers.CharField(),
                "database": serializers.DictField(),
                "assistant": serializers.DictField(),
            },
        ),
    )
    def get(self, request):
        database = {"connected": False}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
            database = {"connected": True, "engine": version.split(",")[0]}
        except DatabaseError:
            logger.exception("Échec de la connexion à PostgreSQL")

        llm = settings.LLM
        assistant_configured = llm["PROVIDER"] not in ("", "none") and bool(llm["MODEL"])
        if llm["PROVIDER"] in ("anthropic", "openai_compatible"):
            assistant_configured = assistant_configured and bool(llm["API_KEY"])

        healthy = database["connected"]
        return Response(
            {
                "status": "ok" if healthy else "degraded",
                "app": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "database": database,
                "assistant": {
                    "configured": assistant_configured,
                    "provider": llm["PROVIDER"] if assistant_configured else None,
                },
            },
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
