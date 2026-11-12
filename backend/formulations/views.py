from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.viewsets import FarmScopedViewSet, ValidationWorkflowMixin
from farms.access import can_review_rations
from governance.activity import log_activity
from governance.models import ValidationStatus
from governance.views import ReadAllWriteReviewers
from governance.workflow import is_reviewer
from seasons.models import Season

from .engine_service import offline_pack, run_formulation
from .models import FeedFormula, FormulaStatus, RationTemplate
from .serializers import (
    CalculationRequestSerializer,
    FeedFormulaSerializer,
    FormulaReviewSerializer,
    RationTemplateSerializer,
    TemplateApplySerializer,
    TemplateFromFormulaSerializer,
)
from .templates import TemplateError, apply_template, matching_templates, template_from_formula


def can_review_formula(user, formula) -> bool:
    """Administrateur, ou nutritionniste / zootechnicien invité (ni le vétérinaire ni le technicien)."""
    return can_review_rations(user, formula.farm)


class FeedFormulaViewSet(FarmScopedViewSet):
    """
    Formules de l'exploitation. Cette étape gère les formules SAISIES MANUELLEMENT (champ `manual_items`) ;
    les formules calculées par le moteur d'optimisation arrivent à l'étape 6.
    """

    queryset = FeedFormula.objects.select_related("farm", "species", "validated_by").prefetch_related(
        "items__ingredient__category"
    )
    serializer_class = FeedFormulaSerializer
    filterset_fields = ["species", "mode", "status", "animal", "group", "is_demo"]
    search_fields = ["name", "notes"]
    ordering_fields = ["created_at", "name", "cost_per_day"]
    ordering = ["-created_at"]
    activity_prefix = "formula"
    review_actions = ("validate", "reject")

    def _review(self, request, new_status, allowed_from, need_reviewer=True, comment_required=False):
        formula = self.get_object()
        payload = FormulaReviewSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        comment = payload.validated_data["comment"]
        if need_reviewer and not can_review_formula(request.user, formula):
            raise PermissionDenied(
                "Seul un expert invité sur l'exploitation ou un administrateur peut se prononcer."
            )
        if formula.status not in allowed_from:
            return Response(
                {
                    "detail": f"Action impossible depuis le statut « {formula.get_status_display()} ».",
                    "code": "invalid_transition",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if comment_required and not comment.strip():
            return Response(
                {"detail": "Un commentaire est obligatoire.", "code": "comment_required"}, status=400
            )
        if new_status == FormulaStatus.VALIDATED:
            if formula.is_demo:
                return Response(
                    {"detail": "Une formule DEMO ne peut pas être validée.", "code": "not_validatable"},
                    status=400,
                )
            if not formula.items.exists():
                return Response(
                    {"detail": "La formule ne contient aucun ingrédient.", "code": "not_validatable"},
                    status=400,
                )
            formula.validated_by = request.user
            formula.validated_at = timezone.now()
        formula.status = new_status
        formula.review_comment = comment
        if new_status == FormulaStatus.PENDING_REVIEW:
            formula.review_requested_at = timezone.now()
        formula.save()
        log_activity(
            request, f"formula.{new_status.lower()}", formula, farm=formula.farm, details={"comment": comment}
        )
        from alerts.engine import refresh_alerts_safely

        # Alerte « formulation à vérifier » : créée à la soumission, résolue à la décision de l'expert.
        refresh_alerts_safely(farm=formula.farm)
        return Response(self.get_serializer(formula).data)

    @extend_schema(
        parameters=[
            OpenApiParameter("farm", int, required=True, description="Exploitation (écriture requise)")
        ],
        responses=OpenApiTypes.OBJECT,
        summary="Paquet de calcul hors ligne : références utilisables, problèmes préparés, profils des lots",
    )
    @action(detail=False, methods=["get"], url_path="offline-pack")
    def offline_pack(self, request):
        from farms.access import can_write_farm
        from farms.models import Farm

        try:
            farm = Farm.objects.get(pk=int(request.query_params.get("farm", "")), is_active=True)
        except (ValueError, Farm.DoesNotExist):
            return Response({"detail": "Exploitation introuvable."}, status=status.HTTP_404_NOT_FOUND)
        if not can_write_farm(request.user, farm):
            # Même règle que le calcul en ligne : réservé aux propriétaires et gestionnaires.
            return Response({"detail": "Exploitation introuvable."}, status=status.HTTP_404_NOT_FOUND)
        return Response(offline_pack(farm))

    @extend_schema(
        request=CalculationRequestSerializer,
        responses=OpenApiTypes.OBJECT,
        summary="Calculer une formule avec le moteur d'optimisation (économique ou équilibré)",
    )
    @action(detail=False, methods=["post"])
    def calculate(self, request):
        payload = CalculationRequestSerializer(data=request.data, context=self.get_serializer_context())
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        profile = {
            "breed": data.get("breed"),
            "category": data.get("category"),
            "physiological_stage": data.get("physiological_stage"),
            "objective": data.get("objective"),
            "weight_kg": data.get("animal_weight_kg"),
            "age_months": data.get("animal_age_months"),
        }
        if data.get("group") is not None:
            profile["head_count"] = data.get("group_head_count")
        formula, result = run_formulation(
            farm=data["farm"],
            user=request.user,
            name=data["name"],
            species=data["species"],
            mode=data["mode"],
            entries=data["ingredients"],
            reference=data.get("reference"),
            profile=profile,
            number_of_animals=data.get("number_of_animals"),
            duration_days=data.get("duration_days"),
            animal=data.get("animal"),
            group=data.get("group"),
            notes=data["notes"],
            extra_warnings=data.get("group_notes", []),
            season=data["season"] if "season" in data else Season.for_date(timezone.localdate()),
            save=data["save"],
        )
        if formula is not None:
            log_activity(
                request,
                "formula.calculated",
                formula,
                farm=formula.farm,
                details={"status": result["status"], "mode": data["mode"]},
            )
        return Response(
            {"formula": self.get_serializer(formula).data if formula else None, "result": result},
            status=status.HTTP_201_CREATED if formula else status.HTTP_200_OK,
        )

    @extend_schema(request=FormulaReviewSerializer, summary="Demander la vérification par un expert")
    @action(detail=True, methods=["post"], url_path="submit-review")
    def submit_review(self, request, pk=None):
        return self._review(
            request,
            FormulaStatus.PENDING_REVIEW,
            {FormulaStatus.DRAFT, FormulaStatus.ESTIMATED, FormulaStatus.REJECTED},
            need_reviewer=False,
        )

    @extend_schema(request=FormulaReviewSerializer, summary="Valider la formule (expert / administrateur)")
    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        return self._review(request, FormulaStatus.VALIDATED, {FormulaStatus.PENDING_REVIEW})

    @extend_schema(request=FormulaReviewSerializer, summary="Rejeter la formule (commentaire obligatoire)")
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._review(
            request,
            FormulaStatus.REJECTED,
            {FormulaStatus.PENDING_REVIEW, FormulaStatus.VALIDATED},
            comment_required=True,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("ids", str, description="Identifiants séparés par des virgules (2 à 5)")
        ],
        summary="Comparer plusieurs formules",
    )
    @action(detail=False, methods=["get"])
    def compare(self, request):
        raw = request.query_params.get("ids", "")
        ids = [int(x) for x in raw.split(",") if x.strip().isdigit()]
        if not 2 <= len(set(ids)) <= 5:
            return Response(
                {"detail": "Indiquez entre 2 et 5 formules à comparer.", "code": "invalid_ids"}, status=400
            )
        formulas = list(self.get_queryset().filter(pk__in=ids))
        if len(formulas) != len(set(ids)):
            return Response({"detail": "Formule introuvable.", "code": "not_found"}, status=404)
        return Response(
            {
                "formulas": FeedFormulaSerializer(
                    formulas, many=True, context=self.get_serializer_context()
                ).data,
                "note": (
                    "Comparaison d'estimations : seules les formules au statut « Validée » "
                    "ont été vérifiées par un expert."
                ),
            }
        )


class RationTemplateViewSet(ValidationWorkflowMixin, viewsets.ModelViewSet):
    """
    Rations types : rédigées et validées par les experts (circuit de validation, source obligatoire).
    Les éleveurs voient les rations types validées (et DEMO) et les appliquent immédiatement à leurs animaux.
    """

    serializer_class = RationTemplateSerializer
    permission_classes = [ReadAllWriteReviewers]
    filterset_fields = [
        "species",
        "category",
        "physiological_stage",
        "objective",
        "season",
        "status",
        "is_demo",
    ]
    search_fields = ["name"]
    ordering = ["name"]

    def get_queryset(self):
        qs = RationTemplate.objects.select_related(
            "species", "category", "physiological_stage", "objective", "season", "source", "validated_by"
        ).prefetch_related("items__ingredient__category")
        if getattr(self, "swagger_fake_view", False) or is_reviewer(self.request.user):
            return qs
        return qs.filter(
            Q(is_demo=False, status=ValidationStatus.VALIDATED)
            | (Q(is_demo=True) & ~Q(status=ValidationStatus.REJECTED))
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        obj = serializer.save()
        self.invalidate_if_needed(obj, serializer.validated_data.keys())

    @extend_schema(
        parameters=[
            OpenApiParameter("farm", int, required=True),
            OpenApiParameter("group", int, required=False),
            OpenApiParameter("animal", int, required=False),
            OpenApiParameter("objective", int, required=False),
            OpenApiParameter("season", int, required=False, description="Par défaut : la saison en cours"),
        ],
        responses=RationTemplateSerializer(many=True),
        summary="Rations types validées applicables à un lot ou à un animal",
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def matching(self, request):
        params = request.query_params
        farm = _readable_farm(request.user, params.get("farm"))
        profile = _target_profile(farm, params.get("group"), params.get("animal"), params.get("objective"))
        season = _season(params.get("season"))
        templates = matching_templates(farm, profile, getattr(season, "pk", None))
        return Response(
            RationTemplateSerializer(templates, many=True, context=self.get_serializer_context()).data
        )

    @extend_schema(
        request=TemplateApplySerializer,
        responses=FeedFormulaSerializer,
        summary="Appliquer une ration type : formule validée immédiatement (sauf DEMO)",
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def apply(self, request, pk=None):
        template = get_object_or_404(self.get_queryset(), pk=pk)
        payload = TemplateApplySerializer(data=request.data, context=self.get_serializer_context())
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        objective = data.get("objective")
        profile = _target_profile(
            data["farm"],
            getattr(data.get("group"), "pk", None),
            getattr(data.get("animal"), "pk", None),
            getattr(objective, "pk", None),
        )
        season = data.get("season") or Season.for_date(timezone.localdate())
        try:
            formula = apply_template(
                template,
                farm=data["farm"],
                user=request.user,
                profile=profile,
                group=data.get("group"),
                animal=data.get("animal"),
                name=data["name"],
                season=season,
            )
        except TemplateError as exc:
            return Response({"detail": exc.message, "code": "template_not_applicable"}, status=400)
        log_activity(
            request, "formula.from_template", formula, farm=formula.farm, details={"template": template.pk}
        )
        return Response(
            FeedFormulaSerializer(formula, context=self.get_serializer_context()).data, status=201
        )

    @extend_schema(
        request=TemplateFromFormulaSerializer,
        responses=RationTemplateSerializer,
        summary="Créer une ration type (brouillon) à partir d'une formule validée",
    )
    @action(detail=False, methods=["post"], url_path="from-formula")
    def from_formula(self, request):
        payload = TemplateFromFormulaSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        formula = data["formula"]
        if not (
            can_review_rations(request.user, formula.farm) or (formula.is_demo and is_reviewer(request.user))
        ):
            raise PermissionDenied(
                "Seul un nutritionniste / zootechnicien de l'exploitation peut créer une ration type."
            )
        try:
            template = template_from_formula(
                formula,
                user=request.user,
                name=data["name"],
                weight_min_kg=data["weight_min_kg"],
                weight_max_kg=data["weight_max_kg"],
                conditions=data["conditions"],
            )
        except TemplateError as exc:
            return Response({"detail": exc.message, "code": "not_a_template"}, status=400)
        return Response(
            RationTemplateSerializer(template, context=self.get_serializer_context()).data, status=201
        )


def _readable_farm(user, farm_id):
    from farms.access import can_read_farm
    from farms.models import Farm

    farm = Farm.objects.filter(pk=farm_id).first() if str(farm_id or "").isdigit() else None
    if farm is None or not can_read_farm(user, farm):
        raise NotFound("Exploitation introuvable.")
    return farm


def _target_profile(farm, group_id, animal_id, objective_id):
    """Profil des animaux visés : lot (valeurs les plus fréquentes, poids moyen) ou animal (sa fiche)."""
    from animals.models import Animal, AnimalGroup
    from animals.services import group_profile

    objective = int(objective_id) if str(objective_id or "").isdigit() else None
    if str(group_id or "").isdigit():
        group = get_object_or_404(AnimalGroup, pk=group_id, farm=farm)
        profile = group_profile(group)
        return {**profile, "objective": objective}
    if str(animal_id or "").isdigit():
        animal = get_object_or_404(Animal, pk=animal_id, farm=farm)
        last = animal.weighings.order_by("-weighed_on").first()
        return {
            "species": animal.species_id,
            "category": animal.category_id,
            "physiological_stage": animal.physiological_stage_id,
            "weight_kg": last.weight_kg if last else animal.initial_weight_kg,
            "objective": objective,
            "head_count": 1,
        }
    raise NotFound("Choisissez un lot ou un animal.")


def _season(season_id):
    if str(season_id or "").isdigit():
        return Season.objects.filter(pk=season_id).first()
    return Season.for_date(timezone.localdate())
