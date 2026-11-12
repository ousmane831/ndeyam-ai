"""
Règles d'accès aux données d'une exploitation — point de vérité unique utilisé par toute l'API.

| Profil                         | Lecture | Écriture | Gestion des membres |
|--------------------------------|---------|----------|---------------------|
| Administrateur de la plateforme| oui     | oui      | oui                 |
| Propriétaire (OWNER)           | oui     | oui      | oui                 |
| Gestionnaire (MANAGER)         | oui     | oui      | non                 |
| Spécialiste invité (EXPERT, VETERINARIAN, TECHNICIAN) | oui | dans son domaine | non |
| Tout autre utilisateur         | non     | non      | non                 |

Domaines des spécialistes invités :
- Nutritionniste / zootechnicien (EXPERT) : vérifie et valide les rations (formules) ;
- Vétérinaire (VETERINARIAN) : observations de santé ;
- Technicien d'élevage (TECHNICIAN) : pesées et observations de suivi.
"""

from .models import (
    OBSERVATION_ROLES,
    RATION_REVIEW_ROLES,
    WEIGHING_ROLES,
    Farm,
    FarmMembership,
    MembershipRole,
)


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


def _has_role(user, farm, roles) -> bool:
    if user and user.is_authenticated and user.is_platform_admin:
        return True
    membership = membership_for(user, farm)
    return bool(membership and membership.role in roles)


def can_record_weighings(user, farm) -> bool:
    """Pesées : propriétaire, gestionnaire, technicien d'élevage."""
    return _has_role(user, farm, WEIGHING_ROLES)


def can_record_observations(user, farm) -> bool:
    """Observations (santé, comportement…) : propriétaire, gestionnaire, technicien, vétérinaire."""
    return _has_role(user, farm, OBSERVATION_ROLES)


def can_review_rations(user, farm) -> bool:
    """Validation des rations : nutritionniste / zootechnicien invité (compte Expert), ou administrateur."""
    if user and user.is_authenticated and user.is_platform_admin:
        return True
    from accounts.models import Role

    return bool(user and user.is_authenticated and user.role == Role.EXPERT) and _has_role(
        user, farm, RATION_REVIEW_ROLES
    )


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
