from django.contrib import admin
from django.db import models

from .models import ActivityLog, ImportBatch, SourceDocument, ValidationRecord


class ValidatedReferenceAdminMixin:
    """Filtres et traçabilité communs aux données de référence (statut, DEMO, auteur)."""

    def get_list_filter(self, request):
        return (*super().get_list_filter(request), "status", "is_demo")

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "source_type", "year", "publisher", "is_demo"]
    list_filter = ["source_type", "is_demo"]
    search_fields = ["title", "authors", "publisher", "identifier"]
    # Une URL saisie sans schéma est supposée en https (comportement par défaut de Django 6).
    formfield_overrides = {models.URLField: {"assume_scheme": "https"}}


@admin.register(ValidationRecord)
class ValidationRecordAdmin(admin.ModelAdmin):
    list_display = ["created_at", "content_type", "object_id", "action", "from_status", "to_status", "actor"]
    list_filter = ["action", "content_type"]
    readonly_fields = [f.name for f in ValidationRecord._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = [
        "started_at",
        "kind",
        "file_name",
        "status",
        "total_rows",
        "created_rows",
        "error_rows",
        "imported_by",
    ]
    list_filter = ["kind", "status", "is_demo"]
    readonly_fields = [f.name for f in ImportBatch._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "actor", "farm", "action", "object_repr"]
    list_filter = ["action"]
    search_fields = ["object_repr", "actor__email"]
    readonly_fields = [f.name for f in ActivityLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
