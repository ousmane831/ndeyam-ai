from django.contrib import admin

from .models import FeedFormula, FeedFormulaIngredient


class FormulaItemInline(admin.TabularInline):
    model = FeedFormulaIngredient
    extra = 0


@admin.register(FeedFormula)
class FeedFormulaAdmin(admin.ModelAdmin):
    list_display = ["name", "farm", "mode", "status", "cost_per_day", "currency", "is_demo", "created_at"]
    list_filter = ["mode", "status", "is_demo", "species"]
    search_fields = ["name", "farm__name"]
    readonly_fields = [
        "result_snapshot",
        "warnings",
        "solver_status",
        "engine_version",
        "validated_by",
        "validated_at",
    ]
    inlines = [FormulaItemInline]
