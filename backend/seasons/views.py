from datetime import date

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.viewsets import FarmScopedViewSet, ValidationWorkflowMixin
from farms.access import can_read_farm
from farms.models import Farm
from governance.models import ValidationStatus
from governance.views import ReadAllWriteReviewers

from .models import IngredientAvailability, Season, SeasonalAdvice
from .serializers import IngredientAvailabilitySerializer, SeasonalAdviceSerializer, SeasonSerializer


class SeasonViewSet(viewsets.ReadOnlyModelViewSet):
    """Calendrier des saisons (géré par l'administration de la plateforme)."""

    queryset = Season.objects.all()
    serializer_class = SeasonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


def visible_advice(farm):
    """Conseils montrés : validés (données réelles) ; DEMO non rejetés pour une exploitation DEMO."""
    qs = SeasonalAdvice.objects.select_related("season", "source")
    if farm is not None and farm.is_demo:
        return qs.filter(is_demo=True).exclude(status=ValidationStatus.REJECTED)
    return qs.filter(is_demo=False, status=ValidationStatus.VALIDATED)


class CurrentSeasonView(APIView):
    """Saison en cours et ses conseils validés (pour l'exploitation demandée)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("farm", int, required=False, description="Exploitation (conseils DEMO si DEMO)"),
            OpenApiParameter(
                "date", str, required=False, description="Date AAAA-MM-JJ (par défaut : aujourd'hui)"
            ),
        ],
        responses=OpenApiTypes.OBJECT,
        summary="Saison en cours, saison suivante et conseils de saison validés",
    )
    def get(self, request):
        try:
            day = (
                date.fromisoformat(request.query_params.get("date", ""))
                if request.query_params.get("date")
                else None
            )
        except ValueError:
            day = None
        day = day or date.today()
        farm = None
        farm_id = request.query_params.get("farm")
        if farm_id and farm_id.isdigit():
            farm = Farm.objects.filter(pk=farm_id).first()
            if farm is not None and not can_read_farm(request.user, farm):
                farm = None
        season = Season.for_date(day)
        seasons = list(Season.objects.all())
        following = None
        if season is not None:
            next_month = season.end_month % 12 + 1
            following = next((s for s in seasons if s.contains(next_month)), None)
        advice = visible_advice(farm).filter(season=season) if season else SeasonalAdvice.objects.none()
        return Response(
            {
                "date": day.isoformat(),
                "season": SeasonSerializer(season).data if season else None,
                "next_season": SeasonSerializer(following).data if following else None,
                "advice": SeasonalAdviceSerializer(advice, many=True).data,
                "pending_advice": SeasonalAdvice.objects.filter(
                    season=season, is_demo=False, status=ValidationStatus.PENDING
                ).count()
                if season
                else 0,
            }
        )


class IngredientAvailabilityViewSet(FarmScopedViewSet):
    """Disponibilité des aliments par saison, déclarée par l'exploitation."""

    queryset = IngredientAvailability.objects.select_related("ingredient", "season")
    serializer_class = IngredientAvailabilitySerializer
    filterset_fields = ["farm", "season", "ingredient", "level"]
    pagination_class = None
    activity_prefix = "availability"


class SeasonalAdviceViewSet(ValidationWorkflowMixin, viewsets.ModelViewSet):
    """Conseils de saison : rédigés et validés par les experts ; les éleveurs ne voient que les validés."""

    queryset = SeasonalAdvice.objects.select_related("season", "source", "validated_by")
    serializer_class = SeasonalAdviceSerializer
    permission_classes = [ReadAllWriteReviewers]
    filterset_fields = ["season", "topic", "status", "is_demo", "species"]
    search_fields = ["title", "text"]
    non_invalidating_fields = ValidationWorkflowMixin.non_invalidating_fields

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        obj = serializer.save()
        self.invalidate_if_needed(obj, serializer.validated_data.keys())
