"""Bases de vues réutilisées par toutes les ressources métier."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from farms.access import can_write_farm, readable_farms
from governance.activity import log_activity
from governance.workflow import WorkflowError, invalidate_after_change, transition

from .permissions import FarmObjectPermission
from .serializers import ValidationActionSerializer


class FarmScopedViewSet(viewsets.ModelViewSet):
    """
    Ressource rattachée à une exploitation (champ `farm`, direct ou via `farm_lookup`).

    - Liste / détail : uniquement les exploitations dont l'utilisateur est membre (sinon 404).
    - Création : exploitation où l'utilisateur peut écrire (propriétaire / gestionnaire).
    - Modification / suppression : idem ; un expert invité reste en lecture seule (403).
    - L'exploitation d'un objet ne peut pas être changée après création.
    """

    farm_lookup = "farm"
    permission_classes = [FarmObjectPermission]
    activity_prefix = None

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, "swagger_fake_view", False):
            return qs.none()
        qs = qs.filter(**{f"{self.farm_lookup}__in": readable_farms(self.request.user)})
        farm_id = self.request.query_params.get("farm")
        if farm_id and farm_id.isdigit():
            qs = qs.filter(**{f"{self.farm_lookup}_id": farm_id})
        return qs

    def get_object_farm(self, obj):
        target = obj
        for part in self.farm_lookup.split("__"):
            target = getattr(target, part)
        return target

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated

        return [IsAuthenticated(), *super().get_permissions()]

    def _log(self, verb, obj):
        if self.activity_prefix:
            log_activity(self.request, f"{self.activity_prefix}.{verb}", obj, farm=self.get_object_farm(obj))

    def perform_create(self, serializer):
        farm = serializer.validated_data.get("farm")
        if farm is not None and not can_write_farm(self.request.user, farm):
            raise PermissionDenied("Vous ne pouvez pas ajouter de données dans cette exploitation.")
        extra = {}
        model_fields = {f.name for f in serializer.Meta.model._meta.fields}
        if "created_by" in model_fields:
            extra["created_by"] = self.request.user
        if "recorded_by" in model_fields:
            extra["recorded_by"] = self.request.user
        if "author" in model_fields:
            extra["author"] = self.request.user
        if "is_demo" in model_fields and farm is not None:
            # Toute donnée saisie dans une exploitation DEMO est DEMO (et inversement) : jamais de mélange.
            extra["is_demo"] = farm.is_demo
        obj = serializer.save(**extra)
        self._log("created", obj)

    def perform_update(self, serializer):
        serializer.validated_data.pop("farm", None)  # l'exploitation est immuable
        obj = serializer.save()
        self._log("updated", obj)

    def perform_destroy(self, instance):
        self._log("deleted", instance)
        instance.delete()


class ValidationWorkflowMixin:
    """Ajoute les actions submit / validate / reject / revert et la remise en brouillon après modification."""

    # Champs dont la modification n'invalide pas la donnée (texte libre).
    non_invalidating_fields = {"observations", "notes", "description", "local_names", "is_active"}

    def _transition(self, request, name):
        obj = self.get_object()
        self.check_workflow_permission(obj, name)
        payload = ValidationActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            transition(obj, name, request.user, payload.validated_data["comment"], request=request)
        except WorkflowError as exc:
            code = status.HTTP_403_FORBIDDEN if exc.code == "forbidden" else status.HTTP_400_BAD_REQUEST
            return Response({"detail": exc.message, "code": exc.code}, status=code)
        from alerts.engine import refresh_alerts_safely

        # Alerte « données à valider » des experts : créée à la soumission, résolue à la décision.
        refresh_alerts_safely(reviewers=True)
        return Response(self.get_serializer(obj).data)

    def check_workflow_permission(self, obj, name):
        """Soumettre : il faut pouvoir modifier l'objet. Les autres actions relèvent du workflow."""
        if name == "submit":
            self.check_object_write(obj)

    def check_object_write(self, obj):
        """À surcharger : lève PermissionDenied si l'utilisateur ne peut pas modifier l'objet."""

    @extend_schema(request=ValidationActionSerializer, summary="Soumettre à validation")
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return self._transition(request, "submit")

    @extend_schema(request=ValidationActionSerializer, summary="Valider (expert / administrateur)")
    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        return self._transition(request, "validate")

    @extend_schema(request=ValidationActionSerializer, summary="Rejeter (commentaire obligatoire)")
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._transition(request, "reject")

    @extend_schema(request=ValidationActionSerializer, summary="Remettre en brouillon")
    @action(detail=True, methods=["post"])
    def revert(self, request, pk=None):
        return self._transition(request, "revert")

    def invalidate_if_needed(self, obj, changed_fields):
        if set(changed_fields) - self.non_invalidating_fields:
            invalidate_after_change(obj, self.request.user, request=self.request)


class ReadOnlyStatusSerializerMixin(serializers.Serializer):
    """Les champs de validation ne sont modifiables que par le workflow, jamais en écriture directe."""

    status = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    validated_by_email = serializers.EmailField(source="validated_by.email", read_only=True, default=None)
    validated_at = serializers.DateTimeField(read_only=True)
    validation_comment = serializers.CharField(read_only=True)
