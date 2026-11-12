from rest_framework import serializers

from core.serializers import ModelCleanMixin, WritableFarmField
from core.viewsets import ReadOnlyStatusSerializerMixin
from nutrition.models import Ingredient
from nutrition.serializers import SourceSummaryField

from .models import IngredientAvailability, Season, SeasonalAdvice


class SeasonSerializer(serializers.ModelSerializer):
    months = serializers.SerializerMethodField()

    class Meta:
        model = Season
        fields = [
            "id",
            "code",
            "name",
            "start_month",
            "end_month",
            "months",
            "is_hot",
            "description",
            "sort_order",
        ]
        read_only_fields = fields

    def get_months(self, obj) -> list[int]:
        return obj.months()


class IngredientAvailabilitySerializer(ModelCleanMixin, serializers.ModelSerializer):
    farm = WritableFarmField()
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.filter(is_active=True))
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)
    season_name = serializers.CharField(source="season.name", read_only=True)
    level_label = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = IngredientAvailability
        fields = [
            "id",
            "farm",
            "ingredient",
            "ingredient_name",
            "season",
            "season_name",
            "level",
            "level_label",
            "notes",
            "is_demo",
            "created_at",
        ]
        read_only_fields = ["id", "is_demo", "created_at"]


class SeasonalAdviceSerializer(ReadOnlyStatusSerializerMixin, serializers.ModelSerializer):
    source = SourceSummaryField(required=False, allow_null=True)
    season_name = serializers.CharField(source="season.name", read_only=True)
    topic_label = serializers.CharField(source="get_topic_display", read_only=True)

    class Meta:
        model = SeasonalAdvice
        fields = [
            "id",
            "season",
            "season_name",
            "species",
            "topic",
            "topic_label",
            "title",
            "text",
            "source",
            "reference_date",
            "is_demo",
            "status",
            "status_label",
            "validated_by_email",
            "validated_at",
            "validation_comment",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
