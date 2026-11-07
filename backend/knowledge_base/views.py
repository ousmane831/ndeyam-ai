from django.db.models import Count, Q
from django.http import FileResponse, Http404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.viewsets import ValidationWorkflowMixin
from governance.activity import log_activity
from governance.workflow import is_reviewer

from .embeddings import configuration_problem
from .ingestion import DuplicateDocumentError, import_document, reindex_document
from .models import TechnicalDocument
from .search import search
from .serializers import (
    ChunkSerializer,
    DocumentUploadSerializer,
    SearchRequestSerializer,
    TechnicalDocumentSerializer,
)


class TechnicalDocumentViewSet(
    ValidationWorkflowMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Base documentaire. Consultation : documents validés pour tous ; tous les documents pour les experts et
    administrateurs, qui seuls importent, modifient, réindexent et valident.
    """

    serializer_class = TechnicalDocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_fields = ["status", "processing_status", "is_demo", "language"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "title"]
    ordering = ["-created_at"]
    http_method_names = ["get", "post", "patch", "delete", "options"]
    non_invalidating_fields = {"description"}

    def get_queryset(self):
        qs = TechnicalDocument.objects.select_related("source", "uploaded_by", "validated_by").annotate(
            chunks_count=Count("chunks"),
            embedded_chunks=Count("chunks", filter=Q(chunks__embedding__isnull=False)),
        )
        if getattr(self, "swagger_fake_view", False) or not is_reviewer(self.request.user):
            qs = qs.filter(status="VALIDATED", is_demo=False)
        return qs

    def _require_reviewer(self):
        if not is_reviewer(self.request.user):
            raise PermissionDenied("La base documentaire est gérée par les experts et les administrateurs.")

    def check_object_write(self, obj):
        self._require_reviewer()

    @extend_schema(
        request=DocumentUploadSerializer, responses=TechnicalDocumentSerializer, summary="Importer un PDF"
    )
    def create(self, request):
        self._require_reviewer()
        payload = DocumentUploadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        try:
            document, warnings = import_document(
                upload=data["file"],
                title=data["title"],
                user=request.user,
                request=request,
                description=data["description"],
                source=data.get("source"),
                language=data["language"],
                is_demo=data["is_demo"],
                reference_date=data.get("reference_date"),
            )
        except DuplicateDocumentError as exc:
            return Response(
                {"detail": str(exc), "code": "duplicate_document", "existing_id": exc.existing.pk}, status=400
            )
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "invalid_file"}, status=400)
        body = self.get_serializer(self.get_queryset().get(pk=document.pk)).data
        return Response({**body, "warnings": warnings}, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        self._require_reviewer()
        document = serializer.save()
        self.invalidate_if_needed(document, serializer.validated_data.keys())
        log_activity(self.request, "document.updated", document)

    def perform_destroy(self, instance):
        self._require_reviewer()
        log_activity(self.request, "document.deleted", instance)
        instance.file.delete(save=False)
        instance.delete()

    @extend_schema(
        request=None,
        responses=OpenApiTypes.OBJECT,
        summary="Réindexer (après changement de modèle d'embeddings)",
    )
    @action(detail=True, methods=["post"])
    def reindex(self, request, pk=None):
        self._require_reviewer()
        document = self.get_object()
        warnings = reindex_document(document, request=request)
        return Response(
            {**self.get_serializer(self.get_queryset().get(pk=document.pk)).data, "warnings": warnings}
        )

    @extend_schema(responses=ChunkSerializer(many=True), summary="Passages indexés du document")
    @action(detail=True, methods=["get"])
    def chunks(self, request, pk=None):
        return Response(ChunkSerializer(self.get_object().chunks.order_by("chunk_index"), many=True).data)

    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY}, summary="Télécharger le PDF")
    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        document = self.get_object()
        if not document.file:
            raise Http404
        return FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=document.file.name.rsplit("/", 1)[-1],
            content_type="application/pdf",
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str),
            OpenApiParameter("k", int),
            OpenApiParameter(
                "include_unvalidated", bool, description="Experts : inclure les documents non validés"
            ),
        ],
        responses=OpenApiTypes.OBJECT,
        summary="Rechercher dans la base documentaire",
    )
    @action(detail=False, methods=["get"])
    def search(self, request):
        params = SearchRequestSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        include = params.validated_data["include_unvalidated"] and is_reviewer(request.user)
        return Response(
            search(params.validated_data["q"], k=params.validated_data["k"], include_unvalidated=include)
        )

    @extend_schema(
        responses=OpenApiTypes.OBJECT, summary="Configuration de la recherche (sans exposer de clé)"
    )
    @action(detail=False, methods=["get"])
    def status(self, request):
        from django.conf import settings

        problem = configuration_problem()
        return Response(
            {
                "embeddings_configured": problem is None,
                "embedding_provider": settings.EMBEDDINGS["PROVIDER"] if problem is None else None,
                "embedding_model": settings.EMBEDDINGS["MODEL"] if problem is None else None,
                "vector_store": settings.VECTOR_STORE_BACKEND,
                "message": problem
                or "Recherche sémantique disponible (repli sur le plein texte si nécessaire).",
            }
        )
