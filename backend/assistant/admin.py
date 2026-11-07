from django.contrib import admin

from .models import AIConversation, AIMessage


class MessageInline(admin.TabularInline):
    model = AIMessage
    extra = 0
    fields = [
        "created_at",
        "role",
        "content",
        "provider",
        "model",
        "input_tokens",
        "output_tokens",
        "latency_ms",
        "error_code",
    ]
    readonly_fields = fields
    can_delete = False


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ["__str__", "user", "farm", "updated_at", "is_archived"]
    search_fields = ["title", "user__email"]
    inlines = [MessageInline]
