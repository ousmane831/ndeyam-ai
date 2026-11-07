from django.contrib import admin

from .models import (
    Animal,
    AnimalCategory,
    AnimalGroup,
    AnimalObservation,
    Breed,
    PhysiologicalStage,
    ProductionObjective,
    Species,
)


class BreedInline(admin.TabularInline):
    model = Breed
    extra = 0


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "scientific_name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]
    inlines = [BreedInline]


@admin.register(Breed)
class BreedAdmin(admin.ModelAdmin):
    list_display = ["name", "species", "local_names", "is_active"]
    list_filter = ["species", "is_active"]
    search_fields = ["name", "local_names"]


@admin.register(AnimalCategory)
class AnimalCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "species", "sort_order"]
    list_filter = ["species"]


@admin.register(PhysiologicalStage)
class PhysiologicalStageAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "species", "sort_order"]
    list_filter = ["species"]


@admin.register(ProductionObjective)
class ProductionObjectiveAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "sort_order"]


@admin.register(AnimalGroup)
class AnimalGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "farm", "species", "is_active", "is_demo"]
    list_filter = ["species", "is_active", "is_demo"]
    search_fields = ["name", "farm__name"]


class ObservationInline(admin.TabularInline):
    model = AnimalObservation
    extra = 0
    exclude = ["author"]


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ["tag_number", "name", "farm", "species", "breed", "sex", "group", "status", "is_demo"]
    list_filter = ["species", "sex", "status", "is_demo", "breed"]
    search_fields = ["tag_number", "name", "farm__name"]
    readonly_fields = ["uuid", "created_at", "updated_at"]
    autocomplete_fields = ["farm", "group"]
    inlines = [ObservationInline]
