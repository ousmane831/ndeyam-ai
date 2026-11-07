from rest_framework import serializers

from core.viewsets import ReadOnlyStatusSerializerMixin
from governance.models import SourceDocument
from nutrition.serializers import SourceSummaryField

from .models import DocumentChunk, TechnicalDocument


class TechnicalDocumentSerializer(ReadOnlyStatusSerializerMixin, serializers.ModelSerializer):
    source = SourceSummaryField(required=False, allow_null=True)
    processing_status_label = serializers.CharField(source="get_processing_status_display", read_only=True)
    chunks_count = serializers.IntegerField(read_only=True, default=0)
    embedded_chunks = serializers.IntegerField(read_only=True, default=0)
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True, default=None)

    class Meta:
        model = TechnicalDocument
        fields = [
            "id",
            "title",
            "description",
            "language",
            "source",
            "reference_date",
            "is_demo",
            "mime_type",
            "size_bytes",
            "page_count",
            "processing_status",
            "processing_status_label",
            "processing_error",
            "indexed_at",
            "embedding_model",
            "chunks_count",
            "embedded_chunks",
            "uploaded_by_email",
            "status",
            "status_label",
            "validated_by_email",
            "validated_at",
            "validation_comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "mime_type",
            "size_bytes",
            "page_count",
            "processing_status",
            "processing_error",
            "indexed_at",
            "embedding_model",
            "is_demo",
            "created_at",
            "updated_at",
        ]


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    title = serializers.CharField(max_length=300)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    source = serializers.PrimaryKeyRelatedField(
        queryset=SourceDocument.objects.all(), required=False, allow_null=True
    )
    language = serializers.CharField(max_length=8, required=False, default="fr")
    reference_date = serializers.DateField(required=False, allow_null=True)
    is_demo = serializers.BooleanField(default=False)

    def validate(self, attrs):
        source = attrs.get("source")
        if source is not None and source.is_demo and not attrs["is_demo"]:
            raise serializers.ValidationError(
                {"source": "Une source DEMO ne peut accompagner qu'un document DEMO."}
            )
        return attrs


class ChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ["id", "chunk_index", "page_start", "page_end", "char_count", "text"]


class SearchRequestSerializer(serializers.Serializer):
    q = serializers.CharField(max_length=500)
    k = serializers.IntegerField(required=False, default=5, min_value=1, max_value=20)
    include_unvalidated = serializers.BooleanField(required=False, default=False)
