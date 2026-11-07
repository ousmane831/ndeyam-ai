from django.contrib import admin

from .models import Farm, FarmMembership


class FarmMembershipInline(admin.TabularInline):
    model = FarmMembership
    extra = 0
    fk_name = "farm"
    autocomplete_fields = ["user"]
    exclude = ["invited_by"]


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ["name", "region", "country", "is_active", "is_demo", "created_at"]
    list_filter = ["country", "region", "is_active", "is_demo"]
    search_fields = ["name", "region", "locality"]
    inlines = [FarmMembershipInline]


@admin.register(FarmMembership)
class FarmMembershipAdmin(admin.ModelAdmin):
    list_display = ["farm", "user", "role", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["farm__name", "user__email"]
    autocomplete_fields = ["farm", "user"]
