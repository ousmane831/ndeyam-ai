from django.db.models import Count, Sum
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from core.csv_io import csv_response
from core.viewsets import FarmScopedViewSet
from governance.activity import log_activity

from .models import FeedingRecord, Ration, RationStatus
from .serializers import EndRationSerializer, FeedingRecordSerializer, RationSerializer


class RationViewSet(FarmScopedViewSet):
    queryset = Ration.objects.select_related("formula", "animal", "group", "farm")
    serializer_class = RationSerializer
    filterset_fields = ["status", "animal", "group", "formula", "is_demo"]
    search_fields = ["name", "notes"]
    ordering_fields = ["start_date", "name"]
    ordering = ["-start_date"]
    activity_prefix = "ration"

    @extend_schema(request=EndRationSerializer, responses=RationSerializer, summary="Terminer la ration")
    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        ration = self.get_object()
        payload = EndRationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        end_date = payload.validated_data["end_date"]
        if end_date < ration.start_date:
            return Response(
                {"detail": "La date de fin doit suivre la date de début.", "code": "invalid_date"}, status=400
            )
        ration.end_date = end_date
        ration.status = RationStatus.ENDED
        ration.save(update_fields=["end_date", "status", "updated_at"])
        log_activity(request, "ration.ended", ration, farm=ration.farm)
        return Response(self.get_serializer(ration).data)


FEEDING_CSV_COLUMNS = [
    ("fed_on", "date"),
    ("ration.name", "ration"),
    ("animal.tag_number", "animal"),
    ("group.name", "lot"),
    ("number_of_animals", "nb_animaux"),
    ("quantity_calculated_kg", "calcule_kg"),
    ("quantity_distributed_kg", "distribue_kg"),
    ("quantity_consumed_kg", "consomme_mesure_kg"),
    ("quantity_refused_kg", "refus_kg"),
    ("estimated_cost", "cout_estime"),
    ("currency", "devise"),
    ("is_demo", "demo"),
    ("notes", "notes"),
]


class FeedingRecordViewSet(FarmScopedViewSet):
    """Historique alimentaire. La quantité consommée n'est jamais déduite de la quantité distribuée."""

    queryset = FeedingRecord.objects.select_related(
        "ration__formula", "animal", "group", "recorded_by", "farm"
    )
    serializer_class = FeedingRecordSerializer
    filterset_fields = {
        "ration": ["exact"],
        "animal": ["exact"],
        "group": ["exact"],
        "fed_on": ["gte", "lte"],
    }
    ordering_fields = ["fed_on", "created_at"]
    ordering = ["-fed_on", "-created_at"]
    activity_prefix = "feeding"

    @extend_schema(summary="Synthèse des quantités et coûts (mêmes filtres que la liste)")
    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.filter_queryset(self.get_queryset())
        totals = qs.aggregate(
            records=Count("id"),
            distributed_kg=Sum("quantity_distributed_kg"),
            calculated_kg=Sum("quantity_calculated_kg"),
            consumed_kg=Sum("quantity_consumed_kg"),
            estimated_cost=Sum("estimated_cost"),
        )
        totals["records_with_measured_consumption"] = qs.filter(quantity_consumed_kg__isnull=False).count()
        totals["records_without_cost"] = qs.filter(estimated_cost__isnull=True).count()
        totals = {k: (str(v) if v is not None and not isinstance(v, int) else v) for k, v in totals.items()}
        totals["note"] = (
            "La consommation totale ne couvre que les distributions où elle a été mesurée ; "
            "le coût ne couvre que les distributions dont la formule a un coût connu."
        )
        return Response(totals)

    @extend_schema(summary="Exporter l'historique alimentaire (CSV)")
    @action(detail=False, methods=["get"])
    def export(self, request):
        return csv_response(
            "historique_alimentaire.csv", FEEDING_CSV_COLUMNS, self.filter_queryset(self.get_queryset())
        )
