from rest_framework import serializers

from core.serializers import ModelCleanMixin

from .models import ActivityLog, ImportBatch, SourceDocument, ValidationRecord


class SourceDocumentSerializer(ModelCleanMixin, serializers.ModelSerializer):
    source_type_label = serializers.CharField(source="get_source_type_display", read_only=True)

    class Meta:
        model = SourceDocument
        fields = [
            "id",
            "title",
            "authors",
            "publisher",
            "year",
            "source_type",
            "source_type_label",
            "identifier",
            "url",
            "notes",
            "is_demo",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ValidationRecordSerializer(serializers.ModelSerializer):
    model = serializers.CharField(source="content_type.model", read_only=True)
    action_label = serializers.CharField(source="get_action_display", read_only=True)
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = ValidationRecord
        fields = [
            "id",
            "model",
            "object_id",
            "action",
            "action_label",
            "from_status",
            "to_status",
            "comment",
            "actor_email",
            "created_at",
        ]


class ImportBatchSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    imported_by_email = serializers.EmailField(source="imported_by.email", read_only=True, default=None)

    class Meta:
        model = ImportBatch
        fields = [
            "id",
            "kind",
            "file_name",
            "status",
            "status_label",
            "total_rows",
            "created_rows",
            "updated_rows",
            "error_rows",
            "errors",
            "is_demo",
            "imported_by_email",
            "started_at",
            "finished_at",
        ]


class ActivityLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)
    farm_name = serializers.CharField(source="farm.name", read_only=True, default=None)
    action_label = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "action",
            "action_label",
            "actor_email",
            "farm",
            "farm_name",
            "object_repr",
            "details",
            "ip_address",
            "created_at",
        ]

    def get_action_label(self, obj) -> str:
        from .activity import action_label

        return action_label(obj.action)
