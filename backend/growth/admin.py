from django.contrib import admin

from governance.admin import ValidatedReferenceAdminMixin

from .models import GrowthMonitoringRange, Weighing


@admin.register(Weighing)
class WeighingAdmin(admin.ModelAdmin):
    list_display = ["animal", "weighed_on", "weight_kg", "method", "recorded_by", "is_demo"]
    list_filter = ["method", "is_demo"]
    search_fields = ["animal__tag_number", "animal__name"]
    date_hierarchy = "weighed_on"


@admin.register(GrowthMonitoringRange)
class GrowthMonitoringRangeAdmin(ValidatedReferenceAdminMixin, admin.ModelAdmin):
    list_display = ["name", "species", "category", "adg_min_g", "adg_max_g", "status", "is_demo"]
    list_filter = ["species"]
    readonly_fields = ["validated_by", "validated_at", "created_by"]
