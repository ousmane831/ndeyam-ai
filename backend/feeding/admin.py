from django.contrib import admin

from .models import FeedingRecord, Ration


@admin.register(Ration)
class RationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "farm",
        "formula",
        "animal",
        "group",
        "start_date",
        "end_date",
        "status",
        "is_demo",
    ]
    list_filter = ["status", "is_demo"]
    search_fields = ["name", "farm__name"]


@admin.register(FeedingRecord)
class FeedingRecordAdmin(admin.ModelAdmin):
    list_display = [
        "fed_on",
        "farm",
        "animal",
        "group",
        "quantity_calculated_kg",
        "quantity_distributed_kg",
        "quantity_consumed_kg",
        "is_demo",
    ]
    list_filter = ["is_demo"]
    date_hierarchy = "fed_on"
