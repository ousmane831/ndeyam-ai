"""
Circuit de validation des données de référence.

    BROUILLON ──submit──▶ EN ATTENTE ──validate──▶ VALIDÉ
        ▲                     │                      │
        └──────revert─────────┴───────reject────▶ REJETÉ

Règles :
- seuls les experts et administrateurs peuvent valider, rejeter ou remettre en brouillon ;
- une donnée DEMO, sans source, ou rattachée à une source DEMO ne peut pas être validée ;
- un rejet exige un commentaire ;
- toute modification d'une donnée validée la remet en brouillon (elle doit être revalidée) ;
- chaque décision est enregistrée dans ValidationRecord et dans le journal d'activité.
"""

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from accounts.models import Role

from .activity import log_activity
from .models import ValidationAction, ValidationRecord, ValidationStatus

S = ValidationStatus


class WorkflowError(Exception):
    def __init__(self, message, code="invalid_transition"):
        super().__init__(message)
        self.message = message
        self.code = code


TRANSITIONS = {
    "submit": {
        "from": {S.DRAFT, S.REJECTED},
        "to": S.PENDING,
        "action": ValidationAction.SUBMITTED,
        "reviewer": False,
    },
    "validate": {
        "from": {S.DRAFT, S.PENDING},
        "to": S.VALIDATED,
        "action": ValidationAction.VALIDATED,
        "reviewer": True,
    },
    "reject": {
        "from": {S.PENDING, S.VALIDATED},
        "to": S.REJECTED,
        "action": ValidationAction.REJECTED,
        "reviewer": True,
    },
    "revert": {
        "from": {S.PENDING, S.VALIDATED, S.REJECTED},
        "to": S.DRAFT,
        "action": ValidationAction.REVERTED,
        "reviewer": True,
    },
}


def is_reviewer(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_platform_admin or user.role == Role.EXPERT))


def validation_blockers(obj) -> list[str]:
    """Raisons empêchant la validation (liste vide = validable)."""
    blockers = []
    if obj.is_demo:
        blockers.append("Une donnée DEMO ne peut pas être validée.")
    if obj.source_id is None:
        blockers.append("Une source documentaire doit être associée avant validation.")
    elif obj.source.is_demo:
        blockers.append("La source associée est une source DEMO : elle ne peut pas justifier une validation.")
    extra = getattr(obj, "extra_validation_blockers", None)
    if callable(extra):
        blockers.extend(extra())
    return blockers


def _record(obj, action, from_status, to_status, user, comment):
    ValidationRecord.objects.create(
        content_type=ContentType.objects.get_for_model(obj),
        object_id=obj.pk,
        action=action,
        from_status=from_status,
        to_status=to_status,
        comment=comment,
        actor=user,
    )


@transaction.atomic
def transition(obj, name, user, comment="", request=None):
    spec = TRANSITIONS.get(name)
    if spec is None:
        raise WorkflowError("Action de validation inconnue.")
    if spec["reviewer"] and not is_reviewer(user):
        raise WorkflowError(
            "Seuls les experts et les administrateurs peuvent effectuer cette action.", "forbidden"
        )
    if obj.status not in spec["from"]:
        raise WorkflowError(
            f"Action impossible depuis le statut « {obj.get_status_display()} ».", "invalid_transition"
        )
    if name == "reject" and not comment.strip():
        raise WorkflowError("Un commentaire est obligatoire pour rejeter une donnée.", "comment_required")
    if name == "validate":
        blockers = validation_blockers(obj)
        if blockers:
            raise WorkflowError(" ".join(blockers), "not_validatable")

    previous = obj.status
    obj.status = spec["to"]
    obj.validation_comment = comment
    if name == "validate":
        obj.validated_by = user
        obj.validated_at = timezone.now()
    elif previous == S.VALIDATED or spec["to"] == S.DRAFT:
        obj.validated_by = None
        obj.validated_at = None
    obj.save()
    _record(obj, spec["action"], previous, obj.status, user, comment)
    log_activity(
        request,
        f"validation.{name}",
        obj,
        actor=user,
        farm=getattr(obj, "farm", None),
        details={"from": previous, "to": obj.status},
    )
    return obj


def invalidate_after_change(obj, user, request=None, reason="Donnée modifiée après validation."):
    """À appeler après la modification d'une donnée : une donnée validée repasse en brouillon."""
    if obj.status != S.VALIDATED:
        return False
    obj.status = S.DRAFT
    obj.validated_by = None
    obj.validated_at = None
    obj.validation_comment = reason
    obj.save(update_fields=["status", "validated_by", "validated_at", "validation_comment", "updated_at"])
    _record(obj, ValidationAction.REVERTED, S.VALIDATED, S.DRAFT, user, reason)
    log_activity(request, "validation.auto_reverted", obj, actor=user, details={"reason": reason})
    return True
