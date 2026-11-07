from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.csv_io import CsvImportError, csv_response
from core.viewsets import FarmScopedViewSet, ValidationWorkflowMixin
from farms.access import can_write_farm, readable_farms
from governance.activity import log_activity
from governance.serializers import ImportBatchSerializer
from governance.views import ReadAllWriteReviewers
from governance.workflow import invalidate_after_change, is_reviewer

from .imports import import_compositions
from .models import (
    InclusionConstraint,
    Ingredient,
    IngredientCategory,
    IngredientComposition,
    IngredientPrice,
    Nutrient,
    NutritionalReference,
    NutritionalRequirement,
    NutritionSystem,
)
from .serializers import (
    CompositionImportSerializer,
    CompositionSerializer,
    InclusionConstraintSerializer,
    IngredientCategorySerializer,
    IngredientDetailSerializer,
    IngredientPriceSerializer,
    IngredientSerializer,
    NutrientSerializer,
    NutritionSystemSerializer,
    ReferenceSerializer,
    RequirementSerializer,
)

# --- Nomenclatures -----------------------------------------------------------------------


class NutritionSystemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NutritionSystem.objects.filter(is_active=True)
    serializer_class = NutritionSystemSerializer
    pagination_class = None


class NutrientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Nutrient.objects.filter(is_active=True).select_related("system")
    serializer_class = NutrientSerializer
    filterset_fields = {"system": ["exact", "isnull"], "category": ["exact"]}
    pagination_class = None


class IngredientCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IngredientCategory.objects.all()
    serializer_class = IngredientCategorySerializer
    pagination_class = None


# --- Ingrédients -------------------------------------------------------------------------


def ingredient_writable(user, ingredient):
    """Catalogue commun : experts / administrateurs. Ingrédient privé : propriétaire / gestionnaire."""
    if ingredient.farm_id is None:
        return is_reviewer(user)
    return can_write_farm(user, ingredient.farm)


def visible_ingredients(user):
    return Ingredient.objects.filter(Q(farm__isnull=True) | Q(farm__in=readable_farms(user)))


class IngredientViewSet(ValidationWorkflowMixin, viewsets.ModelViewSet):
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["category", "status", "is_demo", "is_active", "farm"]
    search_fields = ["name", "local_names", "description"]
    ordering_fields = ["name", "created_at", "status"]
    ordering = ["name"]

    def get_queryset(self):
        qs = visible_ingredients(self.request.user).select_related(
            "category", "source", "validated_by", "farm"
        )
        scope = self.request.query_params.get("scope")
        if scope == "catalog":
            qs = qs.filter(farm__isnull=True)
        elif scope == "private":
            qs = qs.filter(farm__isnull=False)
        return qs

    def get_serializer_class(self):
        return IngredientDetailSerializer if self.action == "retrieve" else IngredientSerializer

    def check_object_write(self, obj):
        if not ingredient_writable(self.request.user, obj):
            raise PermissionDenied("Vous ne pouvez pas modifier cet ingrédient.")

    def perform_create(self, serializer):
        farm = serializer.validated_data.get("farm")
        user = self.request.user
        if farm is None and not is_reviewer(user):
            raise PermissionDenied(
                "Le catalogue commun est géré par les experts. "
                "Choisissez votre exploitation pour un ingrédient privé."
            )
        # Un ingrédient privé d'une exploitation DEMO est toujours DEMO.
        is_demo = serializer.validated_data.get("is_demo", False) or bool(farm and farm.is_demo)
        obj = serializer.save(created_by=user, is_demo=is_demo)
        log_activity(self.request, "ingredient.created", obj, farm=obj.farm)

    def perform_update(self, serializer):
        self.check_object_write(serializer.instance)
        obj = serializer.save()
        self.invalidate_if_needed(obj, serializer.validated_data.keys())
        log_activity(self.request, "ingredient.updated", obj, farm=obj.farm)

    def perform_destroy(self, instance):
        self.check_object_write(instance)
        log_activity(self.request, "ingredient.deleted", instance, farm=instance.farm)
        instance.delete()

    @extend_schema(summary="Exporter les compositions des ingrédients visibles (CSV)")
    @action(detail=False, methods=["get"])
    def export(self, request):
        ingredients = self.filter_queryset(self.get_queryset())
        compositions = (
            IngredientComposition.objects.filter(ingredient__in=ingredients)
            .select_related("ingredient__category", "nutrient__system", "source")
            .order_by("ingredient__name", "nutrient__sort_order")
        )
        columns = [
            ("ingredient.name", "ingredient"),
            ("ingredient.category.code", "categorie"),
            ("nutrient.code", "nutriment"),
            ("nutrient.system.code", "systeme"),
            ("nutrient.unit_label", "unite"),
            ("value", "valeur"),
            ("get_status_display", "statut"),
            ("is_demo", "demo"),
            ("source", "source"),
            ("reference_date", "date_reference"),
        ]
        return csv_response("compositions.csv", columns, compositions)


class CompositionViewSet(ValidationWorkflowMixin, viewsets.ModelViewSet):
    serializer_class = CompositionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["ingredient", "nutrient", "status", "is_demo", "source"]
    ordering = ["ingredient__name", "nutrient__sort_order"]

    def get_queryset(self):
        return IngredientComposition.objects.filter(
            ingredient__in=visible_ingredients(self.request.user)
        ).select_related("ingredient", "nutrient__system", "source", "validated_by")

    def check_object_write(self, obj):
        if not ingredient_writable(self.request.user, obj.ingredient):
            raise PermissionDenied("Vous ne pouvez pas modifier la composition de cet ingrédient.")

    def perform_create(self, serializer):
        ingredient = serializer.validated_data["ingredient"]
        if not visible_ingredients(self.request.user).filter(pk=ingredient.pk).exists():
            raise PermissionDenied("Ingrédient introuvable.")
        if not ingredient_writable(self.request.user, ingredient):
            raise PermissionDenied("Vous ne pouvez pas modifier la composition de cet ingrédient.")
        obj = serializer.save(created_by=self.request.user)
        log_activity(self.request, "composition.created", obj, farm=ingredient.farm)

    def perform_update(self, serializer):
        self.check_object_write(serializer.instance)
        obj = serializer.save()
        self.invalidate_if_needed(obj, serializer.validated_data.keys())
        log_activity(self.request, "composition.updated", obj, farm=obj.ingredient.farm)

    def perform_destroy(self, instance):
        self.check_object_write(instance)
        log_activity(self.request, "composition.deleted", instance, farm=instance.ingredient.farm)
        instance.delete()

    @extend_schema(
        request=CompositionImportSerializer,
        responses=ImportBatchSerializer,
        summary="Importer des compositions (CSV) — experts et administrateurs",
    )
    @action(detail=False, methods=["post"], url_path="import", parser_classes=[MultiPartParser, FormParser])
    def import_csv(self, request):
        if not is_reviewer(request.user):
            raise PermissionDenied("L'import des compositions est réservé aux experts et administrateurs.")
        payload = CompositionImportSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            batch = import_compositions(
                payload.validated_data["file"],
                payload.validated_data["source"],
                payload.validated_data["is_demo"],
                request.user,
                request=request,
            )
        except CsvImportError as exc:
            return Response({"detail": str(exc), "code": "invalid_csv"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ImportBatchSerializer(batch).data, status=status.HTTP_201_CREATED)


# --- Prix --------------------------------------------------------------------------------


class IngredientPriceViewSet(FarmScopedViewSet):
    queryset = IngredientPrice.objects.select_related("ingredient", "farm")
    serializer_class = IngredientPriceSerializer
    filterset_fields = ["ingredient", "currency", "is_demo"]
    ordering_fields = ["valid_from", "price_per_kg_as_fed"]
    ordering = ["-valid_from", "-created_at"]
    activity_prefix = "price"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("latest") == "true":
            # Dernier prix connu de chaque ingrédient, par exploitation.
            qs = qs.order_by("farm_id", "ingredient_id", "-valid_from", "-created_at").distinct(
                "farm_id", "ingredient_id"
            )
        return qs

    def filter_queryset(self, queryset):
        if self.request.query_params.get("latest") == "true":
            return (
                super()
                .filter_queryset(queryset)
                .order_by("farm_id", "ingredient_id", "-valid_from", "-created_at")
            )
        return super().filter_queryset(queryset)

    def perform_create(self, serializer):
        ingredient = serializer.validated_data["ingredient"]
        if not visible_ingredients(self.request.user).filter(pk=ingredient.pk).exists():
            raise PermissionDenied("Ingrédient introuvable.")
        super().perform_create(serializer)


# --- Références nutritionnelles -------------------------------------------------------


class ReferenceViewSet(ValidationWorkflowMixin, viewsets.ModelViewSet):
    """Référentiel des besoins : consultable par tous, géré et validé par les experts / administrateurs."""

    queryset = NutritionalReference.objects.select_related(
        "species", "system", "breed", "category", "physiological_stage", "objective", "source", "validated_by"
    ).prefetch_related("requirements__nutrient")
    serializer_class = ReferenceSerializer
    permission_classes = [ReadAllWriteReviewers]
    filterset_fields = [
        "species",
        "system",
        "status",
        "is_demo",
        "category",
        "physiological_stage",
        "objective",
        "breed",
    ]
    search_fields = ["name", "application_conditions"]
    ordering_fields = ["name", "created_at", "status"]
    ordering = ["species__name", "name"]
    non_invalidating_fields = {"notes"}

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user)
        log_activity(self.request, "reference.created", obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        self.invalidate_if_needed(obj, serializer.validated_data.keys())
        log_activity(self.request, "reference.updated", obj)


class RequirementViewSet(viewsets.ModelViewSet):
    """Besoins d'une référence. Toute modification remet la référence validée en brouillon."""

    queryset = NutritionalRequirement.objects.select_related("nutrient", "reference")
    serializer_class = RequirementSerializer
    permission_classes = [ReadAllWriteReviewers]
    filterset_fields = ["reference", "nutrient", "expression"]
    pagination_class = None

    def _invalidate(self, reference):
        invalidate_after_change(
            reference, self.request.user, request=self.request, reason="Besoins modifiés après validation."
        )

    def perform_create(self, serializer):
        obj = serializer.save()
        self._invalidate(obj.reference)

    def perform_update(self, serializer):
        if (
            "reference" in serializer.validated_data
            and serializer.validated_data["reference"] != serializer.instance.reference
        ):
            raise PermissionDenied("Un besoin ne peut pas être déplacé vers une autre référence.")
        obj = serializer.save()
        self._invalidate(obj.reference)

    def perform_destroy(self, instance):
        reference = instance.reference
        instance.delete()
        self._invalidate(reference)


class InclusionConstraintViewSet(ValidationWorkflowMixin, viewsets.ModelViewSet):
    queryset = InclusionConstraint.objects.select_related(
        "ingredient", "ingredient_category", "source", "validated_by"
    )
    serializer_class = InclusionConstraintSerializer
    permission_classes = [ReadAllWriteReviewers]
    filterset_fields = [
        "species",
        "animal_category",
        "ingredient",
        "ingredient_category",
        "status",
        "is_demo",
    ]
    ordering = ["-created_at"]
    non_invalidating_fields = {"rationale"}

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        obj = serializer.save()
        self.invalidate_if_needed(obj, serializer.validated_data.keys())
