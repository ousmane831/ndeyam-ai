from rest_framework import mixins, viewsets
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated

from core.permissions import IsExpertOrAdmin, IsPlatformAdmin
from governance.activity import log_activity

from .models import ActivityLog, ImportBatch, SourceDocument, ValidationRecord
from .serializers import (
    ActivityLogSerializer,
    ImportBatchSerializer,
    SourceDocumentSerializer,
    ValidationRecordSerializer,
)
from .workflow import is_reviewer


class ReadAllWriteReviewers(BasePermission):
    message = "Seuls les experts et les administrateurs peuvent modifier les données de référence."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or is_reviewer(request.user)


class SourceDocumentViewSet(viewsets.ModelViewSet):
    """Sources documentaires : consultables par tous, gérées par les experts et administrateurs."""

    queryset = SourceDocument.objects.all()
    serializer_class = SourceDocumentSerializer
    permission_classes = [ReadAllWriteReviewers]
    filterset_fields = ["source_type", "is_demo", "year"]
    search_fields = ["title", "authors", "publisher", "identifier"]
    ordering_fields = ["title", "year", "created_at"]
    ordering = ["title"]

    def perform_create(self, serializer):
        source = serializer.save(created_by=self.request.user)
        log_activity(self.request, "source.created", source)

    def perform_update(self, serializer):
        source = serializer.save()
        log_activity(self.request, "source.updated", source)

    def perform_destroy(self, instance):
        # PROTECT : une source utilisée ne peut pas être supprimée (réponse 409 gérée globalement).
        log_activity(self.request, "source.deleted", instance)
        instance.delete()


class ValidationRecordViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Historique des décisions de validation (experts et administrateurs)."""

    queryset = ValidationRecord.objects.select_related("content_type", "actor")
    serializer_class = ValidationRecordSerializer
    permission_classes = [IsAuthenticated, IsExpertOrAdmin]
    filterset_fields = ["action", "content_type__model", "object_id"]
    ordering = ["-created_at"]


class ImportBatchViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Historique des importations : chacun voit les siens, les administrateurs voient tout."""

    queryset = ImportBatch.objects.select_related("imported_by")
    serializer_class = ImportBatchSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["kind", "status"]
    ordering = ["-started_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs if self.request.user.is_platform_admin else qs.filter(imported_by=self.request.user)


class ActivityLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Journal d'activité de la plateforme (administrateurs)."""

    queryset = ActivityLog.objects.select_related("actor", "farm")
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    filterset_fields = ["action", "farm", "actor"]
    search_fields = ["action", "object_repr", "actor__email"]
    ordering = ["-created_at"]
