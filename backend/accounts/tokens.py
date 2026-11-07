"""Révocation des sessions (jetons de rafraîchissement) d'un utilisateur."""

from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


def revoke_all_refresh_tokens(user) -> int:
    """Révoque tous les jetons de rafraîchissement : l'utilisateur est déconnecté de tous ses appareils.

    Les jetons d'accès déjà émis restent valides jusqu'à leur expiration (15 min par défaut).
    """
    revoked = 0
    for token in OutstandingToken.objects.filter(user=user).exclude(blacklistedtoken__isnull=False):
        BlacklistedToken.objects.get_or_create(token=token)
        revoked += 1
    return revoked
