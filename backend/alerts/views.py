from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from farms.access import can_write_farm, readable_farms, writable_farms
from governance.activity import log_activity
from governance.workflow import is_reviewer

from .engine import RULE_DEFINITIONS, evaluate_farm, evaluate_reviewers
from .models import Alert, AlertRule, AlertStatus
from .serializers import AlertActionSerializer, AlertRuleSerializer, AlertSerializer

OPEN = [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]


class AlertViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Alertes visibles par l'utilisateur : celles de ses exploitations et celles qui lui sont adressées.
    Par défaut, seules les alertes ouvertes ou prises en compte sont listées (`?status=` pour les autres).
    """

    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = {
        "alert_type": ["exact"],
        "severity": ["exact"],
        "farm": ["exact"],
        "status": ["exact", "in"],
    }
    search_fields = ["title", "message"]
    ordering_fields = ["created_at", "severity", "due_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Alert.objects.none()
        user = self.request.user
        qs = Alert.objects.filter(Q(farm__in=readable_farms(user)) | Q(recipient=user)).select_related(
            "farm", "rule", "content_type", "resolved_by"
        )
        params = self.request.query_params
        animal_id = params.get("animal")
        if animal_id and animal_id.isdigit():
            from django.contrib.contenttypes.models import ContentType

            from animals.models import Animal

            qs = qs.filter(content_type=ContentType.objects.get_for_model(Animal), object_id=animal_id)
        if self.action == "list" and "status" not in params and "status__in" not in params:
            qs = qs.filter(status__in=OPEN)
        return qs

    def _check_can_act(self, alert):
        user = self.request.user
        if alert.recipient_id == user.pk:
            return
        if alert.farm_id and can_write_farm(user, alert.farm):
            return
        raise PermissionDenied("Vous ne pouvez pas modifier cette alerte (accès en lecture seule).")

    def _set_status(self, request, new_status):
        alert = self.get_object()
        self._check_can_act(alert)
        payload = AlertActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        alert.status = new_status
        if new_status in (AlertStatus.RESOLVED, AlertStatus.DISMISSED):
            alert.resolved_at = timezone.now()
            alert.resolved_by = request.user
        if payload.validated_data["note"]:
            alert.trigger_data = {**alert.trigger_data, "note": payload.validated_data["note"]}
        alert.save()
        log_activity(request, f"alert.{new_status.lower()}", alert, farm=alert.farm)
        return Response(self.get_serializer(alert).data)

    @extend_schema(request=AlertActionSerializer, summary="Prendre en compte")
    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        return self._set_status(request, AlertStatus.ACKNOWLEDGED)

    @extend_schema(request=AlertActionSerializer, summary="Marquer comme résolue")
    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        return self._set_status(request, AlertStatus.RESOLVED)

    @extend_schema(
        request=AlertActionSerializer, summary="Ignorer (non recréée tant que la situation est identique)"
    )
    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        return self._set_status(request, AlertStatus.DISMISSED)

    @extend_schema(summary="Nombre d'alertes ouvertes par niveau et par type")
    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.filter_queryset(self.get_queryset()).filter(status__in=OPEN)
        by_severity = {row["severity"]: row["n"] for row in qs.values("severity").annotate(n=Count("id"))}
        by_type = {row["alert_type"]: row["n"] for row in qs.values("alert_type").annotate(n=Count("id"))}
        return Response({"open": qs.count(), "by_severity": by_severity, "by_type": by_type})

    @extend_schema(
        request=inline_serializer("EvaluateAlerts", {"farm": serializers.IntegerField(required=False)}),
        summary="Réévaluer maintenant les règles (exploitations modifiables par l'utilisateur)",
    )
    @action(detail=False, methods=["post"])
    def evaluate(self, request):
        farms = writable_farms(request.user)
        farm_id = request.data.get("farm")
        if farm_id:
            farms = farms.filter(pk=farm_id)
            if not farms.exists():
                raise PermissionDenied("Exploitation introuvable ou non modifiable.")
        totals = {"created": 0, "updated": 0, "resolved": 0}
        for farm in farms:
            for k, v in evaluate_farm(farm).items():
                totals[k] += v
        if is_reviewer(request.user):
            for k, v in evaluate_reviewers().items():
                totals[k] += v
        return Response(totals)


class AlertRuleViewSet(viewsets.ModelViewSet):
    """
    Réglages des alertes. Règles d'exploitation : propriétaire / gestionnaire.
    Règles par défaut de la plateforme (sans exploitation) : administrateurs.
    """

    serializer_class = AlertRuleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["alert_type", "farm", "is_active"]
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AlertRule.objects.none()
        return AlertRule.objects.filter(Q(farm__in=readable_farms(self.request.user)) | Q(farm__isnull=True))

    def _check_write(self, farm):
        user = self.request.user
        if farm is None and not user.is_platform_admin:
            raise PermissionDenied(
                "Les règles par défaut de la plateforme sont gérées par les administrateurs."
            )
        if farm is not None and not can_write_farm(user, farm):
            raise PermissionDenied("Vous ne pouvez pas modifier les réglages de cette exploitation.")

    def perform_create(self, serializer):
        self._check_write(serializer.validated_data.get("farm"))
        rule = serializer.save(created_by=self.request.user)
        log_activity(self.request, "alert_rule.created", rule, farm=rule.farm)

    def perform_update(self, serializer):
        self._check_write(serializer.instance.farm)
        rule = serializer.save()
        log_activity(
            self.request,
            "alert_rule.updated",
            rule,
            farm=rule.farm,
            details={"parameters": rule.parameters, "is_active": rule.is_active},
        )

    def perform_destroy(self, instance):
        self._check_write(instance.farm)
        instance.delete()

    @extend_schema(summary="Types de règles disponibles, paramètres et valeurs par défaut")
    @action(detail=False, methods=["get"])
    def definitions(self, request):
        return Response(
            [
                {
                    "alert_type": alert_type,
                    "name": d["name"],
                    "description": d["description"],
                    "parameters": [
                        {"name": n, "default": v[0], "min": v[1], "max": v[2], "label": v[3]}
                        for n, v in d["parameters"].items()
                    ],
                    "note": (
                        "Réglages de suivi propres à l'exploitation, pas des recommandations zootechniques."
                    ),
                }
                for alert_type, d in RULE_DEFINITIONS.items()
            ]
        )
