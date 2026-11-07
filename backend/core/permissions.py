"""
Permissions DRF réutilisables.

Principe : une ressource d'une exploitation inaccessible renvoie 404 (elle « n'existe pas » pour
l'utilisateur) ; une ressource visible mais non modifiable renvoie 403.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import Role
from farms.access import can_read_farm, can_write_farm


class IsPlatformAdmin(BasePermission):
    message = "Cette action est réservée aux administrateurs de la plateforme."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_platform_admin)


class IsExpertOrAdmin(BasePermission):
    message = "Cette action est réservée aux experts et aux administrateurs."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_platform_admin or user.role == Role.EXPERT))


class IsBreederOrAdmin(BasePermission):
    message = "Cette action est réservée aux éleveurs et aux administrateurs."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_platform_admin or user.role == Role.ELEVEUR))


class FarmObjectPermission(BasePermission):
    """
    Contrôle objet par objet. La vue doit fournir `get_object_farm(obj)`.
    Lecture : tout membre actif. Écriture : propriétaire ou gestionnaire (ou administrateur).
    """

    message = "Vous n'avez pas le droit de modifier les données de cette exploitation."

    def has_object_permission(self, request, view, obj):
        farm = view.get_object_farm(obj)
        # Actions de vérification (expert invité) : seule la lecture est exigée ici,
        # la vue contrôle ensuite le droit de se prononcer.
        if request.method in SAFE_METHODS or getattr(view, "action", None) in getattr(
            view, "review_actions", ()
        ):
            return can_read_farm(request.user, farm)
        return can_write_farm(request.user, farm)
