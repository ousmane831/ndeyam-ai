from django.contrib import admin

from governance.admin import ValidatedReferenceAdminMixin

from .models import (
    InclusionConstraint,
    Ingredient,
    IngredientCategory,
    IngredientComposition,
    IngredientPrice,
    Nutrient,
    NutritionalReference,
    NutritionalRequirement,
    NutritionSystem,
)


@admin.register(NutritionSystem)
class NutritionSystemAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "version", "is_active"]


@admin.register(Nutrient)
class NutrientAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "unit_label", "system", "is_active"]
    list_filter = ["category", "system", "is_active"]
    search_fields = ["code", "name"]

    @admin.display(description="unité")
    def unit_label(self, obj):
        return obj.unit_label


@admin.register(IngredientCategory)
class IngredientCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "sort_order"]


class CompositionInline(admin.TabularInline):
    model = IngredientComposition
    extra = 0
    fields = ["nutrient", "value", "source", "reference_date", "status", "is_demo"]
    autocomplete_fields = ["source"]


@admin.register(Ingredient)
class IngredientAdmin(ValidatedReferenceAdminMixin, admin.ModelAdmin):
    list_display = ["name", "category", "farm", "status", "is_demo", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "local_names"]
    readonly_fields = ["validated_by", "validated_at", "created_by"]
    inlines = [CompositionInline]


@admin.register(IngredientComposition)
class IngredientCompositionAdmin(ValidatedReferenceAdminMixin, admin.ModelAdmin):
    list_display = ["ingredient", "nutrient", "value", "source", "status", "is_demo"]
    list_filter = ["nutrient"]
    search_fields = ["ingredient__name", "nutrient__code"]
    readonly_fields = ["validated_by", "validated_at", "created_by"]
    autocomplete_fields = ["ingredient", "source"]


@admin.register(IngredientPrice)
class IngredientPriceAdmin(admin.ModelAdmin):
    list_display = [
        "ingredient",
        "farm",
        "price_per_kg_as_fed",
        "currency",
        "valid_from",
        "quantity_available_kg",
        "is_demo",
    ]
    list_filter = ["currency", "is_demo"]
    search_fields = ["ingredient__name", "farm__name", "supplier"]
    autocomplete_fields = ["ingredient", "farm"]


class RequirementInline(admin.TabularInline):
    model = NutritionalRequirement
    extra = 0


@admin.register(NutritionalReference)
class NutritionalReferenceAdmin(ValidatedReferenceAdminMixin, admin.ModelAdmin):
    list_display = ["name", "species", "system", "category", "physiological_stage", "status", "is_demo"]
    list_filter = ["species", "system"]
    search_fields = ["name"]
    readonly_fields = ["validated_by", "validated_at", "created_by"]
    inlines = [RequirementInline]


@admin.register(InclusionConstraint)
class InclusionConstraintAdmin(ValidatedReferenceAdminMixin, admin.ModelAdmin):
    list_display = ["__str__", "species", "animal_category", "status", "is_demo"]
    list_filter = ["species"]
    readonly_fields = ["validated_by", "validated_at", "created_by"]
