"""Écriture dans le journal d'activité (traçabilité des actions sensibles)."""

import logging

from django.contrib.contenttypes.models import ContentType

from .models import ActivityLog

logger = logging.getLogger(__name__)


def client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    return ip or None


def log_activity(request, action, obj=None, *, actor=None, farm=None, details=None):
    """Enregistre une action. Ne bloque jamais l'opération métier si la journalisation échoue."""
    try:
        user = actor or (request.user if request is not None and request.user.is_authenticated else None)
        ActivityLog.objects.create(
            actor=user,
            farm=farm,
            action=action,
            content_type=ContentType.objects.get_for_model(obj) if obj is not None else None,
            object_id=obj.pk if obj is not None else None,
            object_repr=str(obj)[:255] if obj is not None else "",
            details=details or {},
            ip_address=client_ip(request),
        )
    except Exception:  # pragma: no cover - la journalisation ne doit jamais casser une requête
        logger.exception("Impossible d'écrire dans le journal d'activité (%s)", action)


# Libellés français des actions journalisées (tableau de bord, journal d'activité).
# Le test `test_every_logged_action_has_a_label` vérifie que chaque action émise par le code en a un.
_CRUD = {"created": "{} : création", "updated": "{} : modification", "deleted": "{} : suppression"}
_OBJECTS = {
    "group": "Lot",
    "animal": "Animal",
    "ration": "Ration",
    "feeding": "Distribution",
    "formula": "Formule",
    "weighing": "Pesée",
    "price": "Prix",
    "ingredient": "Ingrédient",
    "composition": "Composition",
    "reference": "Référence nutritionnelle",
    "source": "Source documentaire",
    "document": "Document technique",
}
ACTION_LABELS = {
    f"{prefix}.{verb}": text.format(label)
    for prefix, label in _OBJECTS.items()
    for verb, text in _CRUD.items()
}
ACTION_LABELS.update(
    {
        "auth.login": "Connexion",
        "auth.logout": "Déconnexion",
        "account.registered": "Création du compte",
        "account.profile_updated": "Profil modifié",
        "account.password_changed": "Mot de passe modifié",
        "account.password_reset_requested": "Réinitialisation du mot de passe demandée",
        "account.password_reset_completed": "Mot de passe réinitialisé",
        "admin.user_created": "Compte créé par un administrateur",
        "admin.user_updated": "Compte modifié par un administrateur",
        "farm.created": "Création d'une exploitation",
        "farm.updated": "Modification de l'exploitation",
        "farm.member_added": "Ajout d'un membre",
        "farm.member_updated": "Modification d'un membre",
        "farm.member_removed": "Retrait d'un membre",
        "animal.archived": "Sortie d'un animal",
        "animal.restored": "Retour d'un animal",
        "animal.observation_added": "Observation ajoutée",
        "weighing.bulk_created": "Séance de pesée",
        "formula.calculated": "Formule calculée",
        "formula.from_template": "Ration type appliquée",
        "formula.pending_review": "Formule soumise à un expert",
        "formula.validated": "Formule validée par un expert",
        "formula.rejected": "Formule rejetée par un expert",
        "ration.ended": "Ration terminée",
        "alert.acknowledged": "Alerte prise en compte",
        "alert.resolved": "Alerte résolue",
        "alert.dismissed": "Alerte ignorée",
        "alert_rule.created": "Règle d'alerte créée",
        "alert_rule.updated": "Règle d'alerte modifiée",
        "validation.submit": "Donnée soumise à validation",
        "validation.validate": "Donnée validée",
        "validation.reject": "Donnée rejetée",
        "validation.revert": "Donnée remise en brouillon",
        "validation.auto_reverted": "Donnée remise en brouillon après modification",
        "import.animals": "Import d'animaux",
        "import.compositions": "Import de compositions",
        "document.imported": "Document importé",
        "document.reindexed": "Document réindexé",
        "assistant.answered": "Question à l'assistant",
        "assistant.error": "Erreur de l'assistant",
    }
)


def action_label(action):
    return ACTION_LABELS.get(action, action)
