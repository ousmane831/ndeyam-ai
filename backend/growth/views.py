from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from animals.models import Animal, AnimalGroup, AnimalStatus
from core.csv_io import csv_response
from core.viewsets import FarmScopedViewSet, ValidationWorkflowMixin
from farms.access import can_write_farm, readable_farms
from governance.activity import log_activity
from governance.views import ReadAllWriteReviewers

from .models import GrowthMonitoringRange, Weighing
from .prediction import prediction_status
from .serializers import BulkWeighingSerializer, GrowthRangeSerializer, WeighingSerializer
from .services import animal_growth, group_growth

WEIGHING_CSV_COLUMNS = [
    ("animal.tag_number", "animal"),
    ("animal.species.code", "espece"),
    ("animal.breed.name", "race"),
    ("animal.get_sex_display", "sexe"),
    ("animal.birth_date", "date_naissance"),
    ("animal.birth_date_is_estimated", "naissance_estimee"),
    ("weighed_on", "date_pesee"),
    ("weight_kg", "poids_kg"),
    ("get_method_display", "methode"),
    ("is_demo", "demo"),
    ("observations", "observations"),
]


def _refresh_alerts(request, farm):
    """Réévalue les alertes de l'exploitation après une saisie (sans bloquer la requête en cas d'erreur)."""
    from alerts.engine import evaluate_farm

    try:
        evaluate_farm(farm)
    except Exception:  # pragma: no cover - une alerte ne doit jamais empêcher l'enregistrement d'une pesée
        import logging

        logging.getLogger(__name__).exception("Échec de la réévaluation des alertes")


class WeighingViewSet(FarmScopedViewSet):
    queryset = Weighing.objects.select_related("animal__species", "animal__breed", "recorded_by")
    serializer_class = WeighingSerializer
    farm_lookup = "animal__farm"
    filterset_fields = {
        "animal": ["exact"],
        "animal__group": ["exact"],
        "weighed_on": ["gte", "lte"],
        "method": ["exact"],
        "is_demo": ["exact"],
    }
    ordering_fields = ["weighed_on", "weight_kg", "created_at"]
    ordering = ["-weighed_on"]
    activity_prefix = "weighing"

    def perform_create(self, serializer):
        animal = serializer.validated_data["animal"]
        if not can_write_farm(self.request.user, animal.farm):
            raise PermissionDenied("Vous ne pouvez pas enregistrer de pesée dans cette exploitation.")
        weighing = serializer.save(recorded_by=self.request.user, is_demo=animal.is_demo)
        self._log("created", weighing)
        _refresh_alerts(self.request, animal.farm)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        _refresh_alerts(self.request, serializer.instance.animal.farm)

    @extend_schema(
        request=BulkWeighingSerializer,
        responses=WeighingSerializer(many=True),
        summary="Séance de pesée : plusieurs animaux, même date (tout ou rien)",
    )
    @action(detail=False, methods=["post"])
    def bulk(self, request):
        payload = BulkWeighingSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        errors, created, farms = {}, [], set()
        with transaction.atomic():
            for index, entry in enumerate(data["entries"]):
                serializer = WeighingSerializer(
                    data={
                        "animal": entry["animal"],
                        "weight_kg": entry["weight_kg"],
                        "weighed_on": data["weighed_on"],
                        "method": data["method"],
                        "observations": entry["observations"],
                    },
                    context=self.get_serializer_context(),
                )
                if not serializer.is_valid():
                    errors[str(index)] = serializer.errors
                    continue
                animal = serializer.validated_data["animal"]
                if not can_write_farm(request.user, animal.farm):
                    errors[str(index)] = {"animal": ["Vous ne pouvez pas modifier cette exploitation."]}
                    continue
                created.append(serializer.save(recorded_by=request.user, is_demo=animal.is_demo))
                farms.add(animal.farm)
            if errors:
                transaction.set_rollback(True)
                return Response(
                    {
                        "detail": "Aucune pesée n'a été enregistrée : corrigez les lignes en erreur.",
                        "code": "validation_error",
                        "errors": errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        for farm in farms:
            log_activity(request, "weighing.bulk_created", farm=farm, details={"count": len(created)})
            _refresh_alerts(request, farm)
        return Response(
            WeighingSerializer(created, many=True, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(summary="Exporter les pesées (CSV) — base d'un futur jeu d'apprentissage")
    @action(detail=False, methods=["get"])
    def export(self, request):
        return csv_response("pesees.csv", WEIGHING_CSV_COLUMNS, self.filter_queryset(self.get_queryset()))


class AnimalGrowthView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Courbe de poids, écarts, GMD et comparaison à la plage de suivi d'un animal",
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request, pk):
        animal = get_object_or_404(
            Animal.objects.filter(farm__in=readable_farms(request.user)).prefetch_related("weighings"), pk=pk
        )
        return Response({"animal_id": animal.pk, "tag_number": animal.tag_number, **animal_growth(animal)})


class GroupGrowthView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Suivi collectif d'un lot : dernier poids et GMD de chaque animal, GMD moyen",
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request, pk):
        group = get_object_or_404(AnimalGroup.objects.filter(farm__in=readable_farms(request.user)), pk=pk)
        return Response(group_growth(group))


class FarmGrowthOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Dernières pesées de l'exploitation (tableau de bord)", responses=OpenApiTypes.OBJECT
    )
    def get(self, request):
        farms = readable_farms(request.user)
        farm_id = request.query_params.get("farm")
        if farm_id and farm_id.isdigit():
            farms = farms.filter(pk=farm_id)
        weighings = Weighing.objects.filter(animal__farm__in=farms, animal__status=AnimalStatus.ACTIVE)
        latest = weighings.select_related("animal").order_by("-weighed_on", "-created_at")[:10]
        since = timezone.localdate() - timezone.timedelta(days=30)
        return Response(
            {
                "latest_weighings": WeighingSerializer(latest, many=True, context={"request": request}).data,
                "weighings_last_30_days": weighings.filter(weighed_on__gte=since).count(),
                "animals_never_weighed": Animal.objects.filter(
                    farm__in=farms, status=AnimalStatus.ACTIVE, weighings__isnull=True
                ).count(),
            }
        )


class PredictionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Disponibilité d'un modèle de prédiction de croissance", responses=OpenApiTypes.OBJECT
    )
    def get(self, request):
        return Response(prediction_status())


class GrowthRangeViewSet(ValidationWorkflowMixin, viewsets.ModelViewSet):
    """Plages de suivi du GMD : consultables par tous, gérées et validées par experts / administrateurs."""

    queryset = GrowthMonitoringRange.objects.select_related("source", "validated_by")
    serializer_class = GrowthRangeSerializer
    permission_classes = [ReadAllWriteReviewers]
    filterset_fields = ["species", "breed", "category", "physiological_stage", "status", "is_demo"]
    search_fields = ["name"]
    ordering = ["name"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        obj = serializer.save()
        self.invalidate_if_needed(obj, serializer.validated_data.keys())
