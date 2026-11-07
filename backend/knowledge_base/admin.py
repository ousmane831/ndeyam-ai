from django.contrib import admin

from governance.admin import ValidatedReferenceAdminMixin

from .models import DocumentChunk, TechnicalDocument


@admin.register(TechnicalDocument)
class TechnicalDocumentAdmin(ValidatedReferenceAdminMixin, admin.ModelAdmin):
    list_display = ["title", "processing_status", "page_count", "status", "is_demo", "created_at"]
    list_filter = ["processing_status"]
    search_fields = ["title", "description"]
    readonly_fields = [
        "file_sha256",
        "size_bytes",
        "page_count",
        "processing_status",
        "processing_error",
        "indexed_at",
        "embedding_model",
        "validated_by",
        "validated_at",
        "created_by",
    ]


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ["document", "chunk_index", "page_start", "page_end", "char_count", "embedding_model"]
    search_fields = ["text", "document__title"]
    exclude = ["embedding", "search_vector"]
    readonly_fields = [
        "document",
        "chunk_index",
        "text",
        "page_start",
        "page_end",
        "char_count",
        "embedding_model",
    ]
