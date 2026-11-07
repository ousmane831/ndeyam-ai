from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from accounts.models import Role
from core.permissions import FarmObjectPermission
from governance.activity import log_activity

from .access import can_manage_members, readable_farms
from .models import FarmMembership, MembershipRole
from .serializers import FarmMemberSerializer, FarmSerializer


class FarmViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Exploitations accessibles à l'utilisateur.
    Une exploitation inaccessible renvoie 404. Pas de suppression : désactivation via `is_active`.
    """

    serializer_class = FarmSerializer
    permission_classes = [IsAuthenticated, FarmObjectPermission]
    filterset_fields = ["is_active", "country", "region"]
    search_fields = ["name", "region", "locality"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    http_method_names = ["get", "post", "patch", "options"]

    def get_queryset(self):
        return readable_farms(self.request.user)

    def get_object_farm(self, obj):
        return obj

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        if not (user.is_platform_admin or user.role == Role.ELEVEUR):
            raise PermissionDenied(
                "Seuls les éleveurs et les administrateurs peuvent créer une exploitation."
            )
        farm = serializer.save(created_by=user)
        FarmMembership.objects.create(farm=farm, user=user, role=MembershipRole.OWNER)
        log_activity(self.request, "farm.created", farm, farm=farm)

    def perform_update(self, serializer):
        farm = serializer.save()
        log_activity(
            self.request,
            "farm.updated",
            farm,
            farm=farm,
            details={"fields": sorted(self.request.data.keys())},
        )


class FarmMemberViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Membres d'une exploitation. Lecture : tout membre. Gestion : propriétaire ou administrateur."""

    serializer_class = FarmMemberSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "options"]
    pagination_class = None

    def get_farm(self):
        if not hasattr(self, "_farm"):
            # 404 si l'exploitation n'est pas accessible : on ne révèle pas son existence.
            self._farm = get_object_or_404(readable_farms(self.request.user), pk=self.kwargs["farm_pk"])
        return self._farm

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # génération du schéma OpenAPI
            return FarmMembership.objects.none()
        return (
            FarmMembership.objects.filter(farm=self.get_farm())
            .select_related("user")
            .order_by("role", "created_at")
        )

    def get_serializer_context(self):
        if getattr(self, "swagger_fake_view", False):
            return super().get_serializer_context()
        return {**super().get_serializer_context(), "farm": self.get_farm()}

    def check_manage(self):
        if not can_manage_members(self.request.user, self.get_farm()):
            raise PermissionDenied("Seul le propriétaire de l'exploitation peut gérer ses membres.")

    def perform_create(self, serializer):
        self.check_manage()
        membership = serializer.save(farm=self.get_farm(), invited_by=self.request.user)
        log_activity(
            self.request,
            "farm.member_added",
            membership,
            farm=membership.farm,
            details={"user": membership.user.email, "role": membership.role},
        )

    def perform_update(self, serializer):
        self.check_manage()
        membership = serializer.save()
        log_activity(
            self.request,
            "farm.member_updated",
            membership,
            farm=membership.farm,
            details={"role": membership.role, "is_active": membership.is_active},
        )

    def perform_destroy(self, instance):
        self.check_manage()
        if instance.role == MembershipRole.OWNER:
            raise PermissionDenied("Le propriétaire ne peut pas être retiré de son exploitation.")
        log_activity(
            self.request,
            "farm.member_removed",
            instance,
            farm=instance.farm,
            details={"user": instance.user.email},
        )
        instance.delete()
