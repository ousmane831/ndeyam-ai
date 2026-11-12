from django.contrib import admin

from .models import IngredientAvailability, Season, SeasonalAdvice


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "start_month", "end_month", "is_hot", "sort_order"]


@admin.register(IngredientAvailability)
class IngredientAvailabilityAdmin(admin.ModelAdmin):
    list_display = ["ingredient", "farm", "season", "level", "is_demo"]
    list_filter = ["season", "level", "is_demo"]


@admin.register(SeasonalAdvice)
class SeasonalAdviceAdmin(admin.ModelAdmin):
    list_display = ["title", "season", "topic", "status", "is_demo"]
    list_filter = ["season", "topic", "status", "is_demo"]
