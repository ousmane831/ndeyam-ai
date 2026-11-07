"""
Exploitations et adhésions.

L'isolation des données repose sur l'exploitation : un utilisateur n'accède qu'aux exploitations
dont il est membre actif. Un expert n'y accède que si l'exploitation l'a invité (rôle EXPERT,
lecture seule). Les administrateurs de la plateforme voient tout.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import TimeStampedModel


class FarmQuerySet(models.QuerySet):
    def accessible_by(self, user):
        if not user or not user.is_authenticated:
            return self.none()
        if user.is_platform_admin:
            return self.all()
        return self.filter(memberships__user=user, memberships__is_active=True).distinct()


class Farm(TimeStampedModel):
    name = models.CharField("nom", max_length=200)
    country = models.CharField("pays (code ISO)", max_length=2, default="SN")
    region = models.CharField("région", max_length=120, blank=True)
    locality = models.CharField("localité", max_length=200, blank=True)
    description = models.TextField("description", blank=True)
    is_active = models.BooleanField("active", default=True)
    is_demo = models.BooleanField("exploitation DEMO", default=False, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    objects = FarmQuerySet.as_manager()

    class Meta:
        verbose_name = "exploitation"
        verbose_name_plural = "exploitations"
        ordering = ["name"]

    def __str__(self):
        return self.name


class MembershipRole(models.TextChoices):
    OWNER = "OWNER", "Propriétaire"
    MANAGER = "MANAGER", "Gestionnaire"
    EXPERT = "EXPERT", "Expert invité (lecture seule)"


class FarmMembership(TimeStampedModel):
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="farm_memberships"
    )
    role = models.CharField("rôle dans l'exploitation", max_length=16, choices=MembershipRole.choices)
    is_active = models.BooleanField("actif", default=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "membre d'exploitation"
        verbose_name_plural = "membres d'exploitation"
        constraints = [
            models.UniqueConstraint(fields=["farm", "user"], name="farmmembership_unique_user_per_farm"),
            models.UniqueConstraint(
                fields=["farm"], condition=Q(role="OWNER"), name="farmmembership_single_owner"
            ),
        ]

    def __str__(self):
        return f"{self.user} — {self.farm} ({self.get_role_display()})"

    @property
    def can_write(self) -> bool:
        return self.is_active and self.role in (MembershipRole.OWNER, MembershipRole.MANAGER)
