from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.csv_io import CsvImportError, csv_response
from core.serializers import WritableFarmField
from core.viewsets import FarmScopedViewSet
from farms.access import can_write_farm, readable_farms
from governance.activity import log_activity
from governance.serializers import ImportBatchSerializer

from .imports import import_animals
from .models import (
    Animal,
    AnimalCategory,
    AnimalGroup,
    AnimalObservation,
    AnimalStatus,
    Breed,
    PhysiologicalStage,
    ProductionObjective,
    Species,
)
from .serializers import (
    AnimalArchiveSerializer,
    AnimalCategorySerializer,
    AnimalGroupSerializer,
    AnimalObservationSerializer,
    AnimalSerializer,
    BreedSerializer,
    PhysiologicalStageSerializer,
    ProductionObjectiveSerializer,
    SpeciesSerializer,
)
from .services import animal_history


class AnimalImportSerializer(serializers.Serializer):
    farm = WritableFarmField()
    file = serializers.FileField()


# --- Nomenclatures (lecture seule ; gestion via l'administration) ---------------------


class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SpeciesSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Species.objects.all()
        if self.request.query_params.get("include_inactive") != "true":
            qs = qs.filter(is_active=True)
        return qs


class BreedViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Breed.objects.filter(is_active=True, species__is_active=True)
    serializer_class = BreedSerializer
    filterset_fields = ["species"]
    pagination_class = None


class AnimalCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AnimalCategory.objects.filter(species__is_active=True)
    serializer_class = AnimalCategorySerializer
    filterset_fields = ["species"]
    pagination_class = None


class PhysiologicalStageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PhysiologicalStage.objects.filter(species__is_active=True)
    serializer_class = PhysiologicalStageSerializer
    filterset_fields = ["species"]
    pagination_class = None


class ProductionObjectiveViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductionObjective.objects.all()
    serializer_class = ProductionObjectiveSerializer
    pagination_class = None


# --- Lots ------------------------------------------------------------------------------


class AnimalGroupViewSet(FarmScopedViewSet):
    queryset = AnimalGroup.objects.select_related("species")
    serializer_class = AnimalGroupSerializer
    filterset_fields = ["species", "is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    activity_prefix = "group"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(animals_count=Count("animals", filter=Q(animals__status=AnimalStatus.ACTIVE)))
        )


# --- Animaux ---------------------------------------------------------------------------

ANIMAL_CSV_COLUMNS = [
    ("tag_number", "numero"),
    ("name", "nom"),
    ("species.code", "espece"),
    ("breed.name", "race"),
    ("get_sex_display", "sexe"),
    ("birth_date", "date_naissance"),
    ("birth_date_is_estimated", "date_estimee"),
    ("initial_weight_kg", "poids_initial_kg"),
    ("category.name", "categorie"),
    ("physiological_stage.name", "stade"),
    ("group.name", "lot"),
    ("registered_on", "date_enregistrement"),
    ("get_status_display", "statut"),
    ("is_demo", "demo"),
    ("observations", "observations"),
]


class AnimalViewSet(FarmScopedViewSet):
    queryset = Animal.objects.select_related(
        "species", "breed", "category", "physiological_stage", "group", "farm"
    )
    serializer_class = AnimalSerializer
    filterset_fields = {
        "species": ["exact"],
        "breed": ["exact"],
        "sex": ["exact"],
        "group": ["exact", "isnull"],
        "status": ["exact", "in"],
        "category": ["exact"],
        "physiological_stage": ["exact"],
        "is_demo": ["exact"],
    }
    search_fields = ["tag_number", "name", "observations"]
    ordering_fields = ["tag_number", "name", "birth_date", "registered_on", "created_at"]
    ordering = ["tag_number"]
    activity_prefix = "animal"

    def get_queryset(self):
        qs = super().get_queryset()
        # Par défaut, seuls les animaux présents sont listés (les archivés restent consultables par filtre).
        if (
            self.action == "list"
            and "status" not in self.request.query_params
            and "status__in" not in self.request.query_params
        ):
            qs = qs.filter(status=AnimalStatus.ACTIVE)
        return qs

    @extend_schema(
        request=AnimalArchiveSerializer, responses=AnimalSerializer, summary="Archiver (vendu, mort, archivé)"
    )
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        animal = self.get_object()
        payload = AnimalArchiveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        animal.status = payload.validated_data["status"]
        animal.archived_at = timezone.now()
        note = payload.validated_data.get("note")
        if note:
            AnimalObservation.objects.create(
                animal=animal, text=f"Sortie : {note}", kind="OTHER", author=request.user
            )
        animal.save(update_fields=["status", "archived_at", "updated_at"])
        log_activity(request, "animal.archived", animal, farm=animal.farm, details={"status": animal.status})
        return Response(self.get_serializer(animal).data)

    @extend_schema(request=None, responses=AnimalSerializer, summary="Remettre l'animal parmi les présents")
    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        animal = self.get_object()
        animal.status = AnimalStatus.ACTIVE
        animal.archived_at = None
        animal.save(update_fields=["status", "archived_at", "updated_at"])
        log_activity(request, "animal.restored", animal, farm=animal.farm)
        return Response(self.get_serializer(animal).data)

    @extend_schema(
        summary="Historique chronologique de l'animal (pesées, observations, rations, alimentation)"
    )
    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return Response(animal_history(self.get_object()))

    @extend_schema(
        request=AnimalImportSerializer, responses=ImportBatchSerializer, summary="Importer des animaux (CSV)"
    )
    @action(detail=False, methods=["post"], url_path="import", parser_classes=[MultiPartParser, FormParser])
    def import_csv(self, request):
        payload = AnimalImportSerializer(data=request.data, context={"request": request})
        payload.is_valid(raise_exception=True)
        try:
            batch = import_animals(payload.validated_data["file"], payload.validated_data["farm"], request)
        except CsvImportError as exc:
            return Response({"detail": str(exc), "code": "invalid_csv"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ImportBatchSerializer(batch).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Exporter les animaux (CSV, mêmes filtres que la liste)")
    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        animals = self.filter_queryset(self.get_queryset())
        return csv_response("animaux.csv", ANIMAL_CSV_COLUMNS, animals)


class AnimalObservationViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """Observations d'un animal (route imbriquée /animals/{id}/observations/)."""

    serializer_class = AnimalObservationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_animal(self):
        if not hasattr(self, "_animal"):
            self._animal = get_object_or_404(
                Animal.objects.filter(farm__in=readable_farms(self.request.user)), pk=self.kwargs["animal_pk"]
            )
        return self._animal

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AnimalObservation.objects.none()
        return self.get_animal().observation_entries.select_related("author")

    def _check_write(self):
        if not can_write_farm(self.request.user, self.get_animal().farm):
            raise PermissionDenied("Vous ne pouvez pas modifier les données de cette exploitation.")

    def perform_create(self, serializer):
        self._check_write()
        obs = serializer.save(animal=self.get_animal(), author=self.request.user)
        log_activity(self.request, "animal.observation_added", obs, farm=obs.animal.farm)

    def perform_destroy(self, instance):
        self._check_write()
        instance.delete()
