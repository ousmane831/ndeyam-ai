"""
Règles d'accès aux données d'une exploitation — point de vérité unique utilisé par toute l'API.

| Profil                         | Lecture | Écriture | Gestion des membres |
|--------------------------------|---------|----------|---------------------|
| Administrateur de la plateforme| oui     | oui      | oui                 |
| Propriétaire (OWNER)           | oui     | oui      | oui                 |
| Gestionnaire (MANAGER)         | oui     | oui      | non                 |
| Expert invité (EXPERT)         | oui     | non      | non                 |
| Tout autre utilisateur         | non     | non      | non                 |
"""

from .models import Farm, FarmMembership, MembershipRole


def membership_for(user, farm):
    if not user or not user.is_authenticated:
        return None
    farm_id = farm.pk if isinstance(farm, Farm) else farm
    return FarmMembership.objects.filter(farm_id=farm_id, user=user, is_active=True).first()


def can_read_farm(user, farm) -> bool:
    if user and user.is_authenticated and user.is_platform_admin:
        return True
    return membership_for(user, farm) is not None


def can_write_farm(user, farm) -> bool:
    if user and user.is_authenticated and user.is_platform_admin:
        return True
    membership = membership_for(user, farm)
    return bool(membership and membership.can_write)


def can_manage_members(user, farm) -> bool:
    if user and user.is_authenticated and user.is_platform_admin:
        return True
    membership = membership_for(user, farm)
    return bool(membership and membership.role == MembershipRole.OWNER)


def readable_farms(user):
    return Farm.objects.accessible_by(user)


def writable_farms(user):
    if user and user.is_authenticated and user.is_platform_admin:
        return Farm.objects.all()
    return Farm.objects.filter(
        memberships__user=user,
        memberships__is_active=True,
        memberships__role__in=[MembershipRole.OWNER, MembershipRole.MANAGER],
    ).distinct()
