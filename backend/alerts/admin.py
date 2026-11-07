from django.contrib import admin

from .models import Alert, AlertRule


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "alert_type", "farm", "is_active"]
    list_filter = ["alert_type", "is_active"]


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["title", "alert_type", "severity", "farm", "recipient", "status", "created_at"]
    list_filter = ["alert_type", "severity", "status"]
    search_fields = ["title", "message", "rule_code"]
    readonly_fields = ["rule_code", "trigger_data", "dedup_key"]
