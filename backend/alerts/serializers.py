from rest_framework import serializers

from core.serializers import WritableFarmField

from .engine import RULE_DEFINITIONS, validate_parameters
from .models import Alert, AlertRule


class AlertSerializer(serializers.ModelSerializer):
    alert_type_label = serializers.CharField(source="get_alert_type_display", read_only=True)
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    farm_name = serializers.CharField(source="farm.name", read_only=True, default=None)
    target = serializers.SerializerMethodField()
    rule_name = serializers.CharField(source="rule.name", read_only=True, default=None)
    resolved_by_email = serializers.EmailField(source="resolved_by.email", read_only=True, default=None)

    class Meta:
        model = Alert
        fields = [
            "id",
            "farm",
            "farm_name",
            "alert_type",
            "alert_type_label",
            "severity",
            "severity_label",
            "title",
            "message",
            "rule_code",
            "rule_name",
            "trigger_data",
            "target",
            "status",
            "status_label",
            "due_date",
            "resolved_at",
            "resolved_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_target(self, obj) -> dict | None:
        if obj.content_type_id is None:
            return None
        return {"type": obj.content_type.model, "id": obj.object_id}


class AlertRuleSerializer(serializers.ModelSerializer):
    farm = WritableFarmField(required=False, allow_null=True)
    alert_type_label = serializers.CharField(source="get_alert_type_display", read_only=True)
    scope = serializers.SerializerMethodField()

    class Meta:
        model = AlertRule
        fields = [
            "id",
            "farm",
            "scope",
            "alert_type",
            "alert_type_label",
            "name",
            "description",
            "parameters",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"name": {"required": False}}  # nom par défaut du type de règle si absent
        validators = []  # unicité vérifiée ci-dessous avec un message explicite

    def get_scope(self, obj) -> str:
        return "farm" if obj.farm_id else "platform"

    def validate(self, attrs):
        alert_type = attrs.get("alert_type", getattr(self.instance, "alert_type", None))
        farm = attrs.get("farm", getattr(self.instance, "farm", None))
        if self.instance is not None:
            for field in ("alert_type", "farm"):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError({field: "Ce champ ne peut pas être modifié."})
        if farm is not None and alert_type == "REFERENCE_TO_VALIDATE":
            raise serializers.ValidationError(
                {"alert_type": "Cette règle concerne uniquement les experts (plateforme)."}
            )
        try:
            attrs["parameters"] = validate_parameters(
                alert_type, attrs.get("parameters", getattr(self.instance, "parameters", {}))
            )
        except ValueError as exc:
            raise serializers.ValidationError({"parameters": str(exc)}) from exc
        qs = AlertRule.objects.filter(alert_type=alert_type, farm=farm)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                {"alert_type": "Une règle de ce type existe déjà pour ce périmètre."}
            )
        if not attrs.get("name") and self.instance is None:
            attrs["name"] = RULE_DEFINITIONS[alert_type]["name"]
        return attrs


class AlertActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")
