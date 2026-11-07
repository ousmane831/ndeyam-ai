"""
Historique des conversations avec l'assistant.

`provenance` conserve, pour chaque réponse, l'origine de chaque information :
base de données, document (avec références), moteur nutritionnel ou explication du LLM.
"""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class AIConversation(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_conversations"
    )
    farm = models.ForeignKey("farms.Farm", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    title = models.CharField("titre", max_length=255, blank=True)
    is_archived = models.BooleanField("archivée", default=False)

    class Meta:
        verbose_name = "conversation IA"
        verbose_name_plural = "conversations IA"
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user", "-updated_at"])]

    def __str__(self):
        return self.title or f"Conversation #{self.pk}"


class MessageRole(models.TextChoices):
    USER = "USER", "Utilisateur"
    ASSISTANT = "ASSISTANT", "Assistant"
    TOOL = "TOOL", "Outil métier"
    SYSTEM = "SYSTEM", "Système"


class AIMessage(models.Model):
    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=MessageRole.choices)
    content = models.TextField("contenu")
    provenance = models.JSONField("provenance des informations", default=list, blank=True)
    tool_calls = models.JSONField("appels d'outils", default=list, blank=True)
    provider = models.CharField(max_length=32, blank=True)
    model = models.CharField(max_length=150, blank=True)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "message IA"
        verbose_name_plural = "messages IA"
        ordering = ["created_at", "id"]  # départage les messages créés dans la même milliseconde

    def __str__(self):
        return f"{self.get_role_display()} — {self.content[:60]}"
