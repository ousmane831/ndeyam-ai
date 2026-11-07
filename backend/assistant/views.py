from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from farms.access import readable_farms
from farms.models import Farm

from .models import AIConversation, AIMessage
from .orchestrator import ask, assistant_status


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = [
            "id",
            "role",
            "content",
            "provenance",
            "tool_calls",
            "provider",
            "model",
            "error_code",
            "latency_ms",
            "created_at",
        ]


class ConversationSerializer(serializers.ModelSerializer):
    farm = serializers.PrimaryKeyRelatedField(queryset=Farm.objects.all(), required=False, allow_null=True)
    messages_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = AIConversation
        fields = ["id", "title", "farm", "is_archived", "messages_count", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_farm(self, farm):
        if farm is not None and not readable_farms(self.context["request"].user).filter(pk=farm.pk).exists():
            raise serializers.ValidationError("Exploitation introuvable ou non accessible.")
        return farm


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = [*ConversationSerializer.Meta.fields, "messages"]


class AskSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=2000, trim_whitespace=True)


class ConversationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Conversations de l'utilisateur connecté (strictement privées)."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "options"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return AIConversation.objects.none()
        from django.db.models import Count

        return AIConversation.objects.filter(user=self.request.user).annotate(
            messages_count=Count("messages")
        )

    def get_serializer_class(self):
        return ConversationDetailSerializer if self.action == "retrieve" else ConversationSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_throttles(self):
        if self.action == "messages":
            self.throttle_scope = "assistant"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    @extend_schema(
        request=AskSerializer,
        responses=MessageSerializer(many=True),
        summary="Poser une question à l'assistant",
    )
    @action(detail=True, methods=["post"])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        payload = AskSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        question, reply = ask(conversation, payload.validated_data["content"], request=request)
        code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if reply.error_code == "not_configured"
            else status.HTTP_201_CREATED
        )
        return Response(MessageSerializer([question, reply], many=True).data, status=code)

    @extend_schema(
        responses=OpenApiTypes.OBJECT, summary="L'assistant est-il configuré ? (sans exposer de clé)"
    )
    @action(detail=False, methods=["get"])
    def status(self, request):
        return Response(assistant_status())
