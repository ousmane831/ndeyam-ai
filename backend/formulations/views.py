from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.models import Role
from core.viewsets import FarmScopedViewSet
from farms.access import membership_for
from governance.activity import log_activity

from .engine_service import run_formulation
from .models import FeedFormula, FormulaStatus
from .serializers import CalculationRequestSerializer, FeedFormulaSerializer, FormulaReviewSerializer


def can_review_formula(user, formula) -> bool:
    """Administrateur, ou expert invité sur l'exploitation de la formule."""
    if user.is_platform_admin:
        return True
    return user.role == Role.EXPERT and membership_for(user, formula.farm) is not None


class FeedFormulaViewSet(FarmScopedViewSet):
    """
    Formules de l'exploitation. Cette étape gère les formules SAISIES MANUELLEMENT (champ `manual_items`) ;
    les formules calculées par le moteur d'optimisation arrivent à l'étape 6.
    """

    queryset = FeedFormula.objects.select_related("farm", "species", "validated_by").prefetch_related(
        "items__ingredient"
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
        formula.save()
        log_activity(
            request, f"formula.{new_status.lower()}", formula, farm=formula.farm, details={"comment": comment}
        )
        from alerts.engine import refresh_alerts_safely

        # Alerte « formulation à vérifier » : créée à la soumission, résolue à la décision de l'expert.
        refresh_alerts_safely(farm=formula.farm)
        return Response(self.get_serializer(formula).data)

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
