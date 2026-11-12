"""
Moteur d'alertes et de rappels.

Chaque règle produit des « candidats » à partir des données enregistrées. La synchronisation :
- crée les alertes nouvelles ;
- met à jour le texte des alertes encore ouvertes ;
- résout automatiquement celles dont la condition n'est plus remplie ;
- ne recrée pas une alerte que l'utilisateur a ignorée ou résolue, tant que la situation est identique
  (la clé d'unicité encode la situation : date de la dernière pesée, champs manquants, etc.).

Les seuils (intervalle de pesée, délai de suivi) sont des RÉGLAGES DE SUIVI configurables par
exploitation : ce ne sont pas des recommandations zootechniques. Les alertes de croissance ne
s'appuient que sur des plages de suivi VALIDÉES et ne constituent jamais un diagnostic vétérinaire.
"""

from dataclasses import dataclass, field
from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import Alert, AlertRule, AlertSeverity, AlertStatus, AlertType

NOT_A_DIAGNOSIS = (
    "Cette alerte signale un écart par rapport à une plage de suivi ; "
    "ce n'est pas un diagnostic vétérinaire. "
    "En cas de doute sur la santé de l'animal, consultez un vétérinaire."
)

# Paramètres par défaut et bornes autorisées (type -> paramètre -> (défaut, min, max, libellé)).
RULE_DEFINITIONS = {
    AlertType.WEIGHING_REMINDER: {
        "name": "Rappel de pesée",
        "description": "Animal non pesé depuis l'intervalle de suivi choisi par l'exploitation.",
        "parameters": {"interval_days": (30, 1, 365, "Intervalle entre deux pesées (jours)")},
    },
    AlertType.FOLLOW_UP_REMINDER: {
        "name": "Rappel de suivi alimentaire",
        "description": "Ration en cours sans distribution enregistrée depuis le délai choisi.",
        "parameters": {"days_without_record": (7, 1, 90, "Délai sans enregistrement (jours)")},
    },
    AlertType.MISSING_DATA: {
        "name": "Informations manquantes",
        "description": "Informations d'un animal nécessaires au suivi et à la formulation.",
        "parameters": {},
    },
    AlertType.GROWTH_OUT_OF_RANGE: {
        "name": "Croissance hors plage de suivi",
        "description": "Dernier GMD mesuré en dehors d'une plage de suivi validée par un expert.",
        "parameters": {},
    },
    AlertType.FORMULA_TO_REVIEW: {
        "name": "Formulation à vérifier",
        "description": "Formule en attente de vérification par un expert.",
        "parameters": {},
    },
    AlertType.REFERENCE_TO_VALIDATE: {
        "name": "Données de référence à valider",
        "description": "Données de référence soumises, en attente de validation (experts, administrateurs).",
        "parameters": {},
    },
}

FARM_RULE_TYPES = [t for t in RULE_DEFINITIONS if t != AlertType.REFERENCE_TO_VALIDATE]


@dataclass
class Candidate:
    dedup_key: str
    alert_type: str
    title: str
    message: str
    rule_code: str
    severity: str = AlertSeverity.INFO
    trigger_data: dict = field(default_factory=dict)
    target: object = None
    due_date: date | None = None


def validate_parameters(alert_type, parameters):
    """Retourne les paramètres normalisés ou lève ValueError avec un message en français."""
    definition = RULE_DEFINITIONS[alert_type]["parameters"]
    clean = {}
    unknown = set(parameters or {}) - set(definition)
    if unknown:
        raise ValueError(f"Paramètre(s) inconnu(s) : {', '.join(sorted(unknown))}.")
    for name, (default, low, high, label) in definition.items():
        value = (parameters or {}).get(name, default)
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} : nombre entier attendu.") from exc
        if not low <= value <= high:
            raise ValueError(f"{label} : valeur entre {low} et {high} attendue.")
        clean[name] = value
    return clean


def effective_rule(alert_type, farm):
    """Règle applicable : celle de l'exploitation, sinon celle de la plateforme, sinon les défauts."""
    rules = {
        r.farm_id: r
        for r in AlertRule.objects.filter(alert_type=alert_type, farm__in=[farm])
        | AlertRule.objects.filter(alert_type=alert_type, farm__isnull=True)
    }
    rule = rules.get(getattr(farm, "pk", None)) or rules.get(None)
    if rule is None:
        return None, validate_parameters(alert_type, {}), True
    return rule, validate_parameters(alert_type, rule.parameters), rule.is_active


# --- Règles d'exploitation ----------------------------------------------------------------


def _active_animals(farm):
    from animals.models import AnimalStatus

    return (
        farm.animals.filter(status=AnimalStatus.ACTIVE)
        .select_related("species", "breed", "category", "physiological_stage")
        .prefetch_related("weighings")
    )


def rule_weighing_reminder(farm, params, today):
    interval = params["interval_days"]
    for animal in _active_animals(farm):
        last = max((w.weighed_on for w in animal.weighings.all()), default=None)
        reference = last or animal.registered_on
        days = (today - reference).days
        if days < interval:
            continue
        since = (
            f"Dernière pesée le {last:%d/%m/%Y}"
            if last
            else f"Aucune pesée depuis l'enregistrement ({reference:%d/%m/%Y})"
        )
        yield Candidate(
            dedup_key=f"weighing_reminder:{animal.pk}:{reference.isoformat()}",
            alert_type=AlertType.WEIGHING_REMINDER,
            severity=AlertSeverity.WARNING if days >= 2 * interval else AlertSeverity.INFO,
            title=f"Pesée à prévoir : {animal}",
            message=f"{since}, soit il y a {days} jours. Intervalle de suivi configuré : {interval} jours.",
            rule_code="weighing_interval",
            trigger_data={
                "last_weighing_on": last.isoformat() if last else None,
                "reference_date": reference.isoformat(),
                "days_since": days,
                "interval_days": interval,
            },
            target=animal,
            due_date=reference + timezone.timedelta(days=interval),
        )


def rule_missing_data(farm, params, today):
    for animal in _active_animals(farm):
        missing = []
        if animal.birth_date is None:
            missing.append("date de naissance ou âge estimé")
        if animal.initial_weight_kg is None and not animal.weighings.all():
            missing.append("aucun poids enregistré")
        if animal.category_id is None:
            missing.append("catégorie")
        if animal.physiological_stage_id is None:
            missing.append("stade physiologique")
        if not missing:
            continue
        yield Candidate(
            dedup_key=f"missing_data:{animal.pk}:{'|'.join(missing)}",
            alert_type=AlertType.MISSING_DATA,
            title=f"Informations à compléter : {animal}",
            message=(
                f"Informations manquantes : {', '.join(missing)}. "
                "Elles sont nécessaires au suivi de croissance et au choix d'une référence nutritionnelle."
            ),
            rule_code="animal_missing_fields",
            trigger_data={"missing_fields": missing},
            target=animal,
        )


def rule_growth_out_of_range(farm, params, today):
    from growth.services import animal_growth

    for animal in _active_animals(farm):
        growth = animal_growth(animal)
        position = growth["latest_vs_range"]
        if position not in ("below", "above"):
            continue
        interval, growth_range = growth["latest_interval"], growth["monitoring_range"]
        direction = "inférieur" if position == "below" else "supérieur"
        yield Candidate(
            dedup_key=f"growth_range:{animal.pk}:{interval['to']}",
            alert_type=AlertType.GROWTH_OUT_OF_RANGE,
            severity=AlertSeverity.WARNING,
            title=f"Croissance hors plage de suivi : {animal}",
            message=(
                f"GMD de {interval['adg_g_per_day']} g/j entre le {interval['from']:%d/%m/%Y} et le "
                f"{interval['to']:%d/%m/%Y}, {direction} à la plage « {growth_range['name']} » "
                f"({growth_range['adg_min_g'] or '—'} à {growth_range['adg_max_g'] or '—'} g/j ; "
                f"source : {growth_range['source']}). {NOT_A_DIAGNOSIS}"
            ),
            rule_code="adg_outside_validated_range",
            trigger_data={
                "adg_g_per_day": interval["adg_g_per_day"],
                "interval_from": interval["from"].isoformat(),
                "interval_to": interval["to"].isoformat(),
                "low_reliability": interval["low_reliability"],
                "position": position,
                "range": growth_range,
            },
            target=animal,
        )


def rule_follow_up(farm, params, today):
    from feeding.models import RationStatus

    delay = params["days_without_record"]
    for ration in farm.rations.filter(status=RationStatus.ACTIVE, start_date__lte=today).prefetch_related(
        "records"
    ):
        last = max((r.fed_on for r in ration.records.all()), default=None)
        reference = last or ration.start_date
        days = (today - reference).days
        if days < delay:
            continue
        since = (
            f"dernière distribution enregistrée le {last:%d/%m/%Y}"
            if last
            else "aucune distribution enregistrée"
        )
        yield Candidate(
            dedup_key=f"follow_up:{ration.pk}:{reference.isoformat()}",
            alert_type=AlertType.FOLLOW_UP_REMINDER,
            title=f"Suivi alimentaire à compléter : {ration.name}",
            message=f"Ration en cours, {since} ({days} jours). Délai de suivi configuré : {delay} jours.",
            rule_code="ration_without_records",
            trigger_data={
                "last_record_on": last.isoformat() if last else None,
                "days_since": days,
                "days_without_record": delay,
            },
            target=ration,
        )


def review_due(formula):
    """Réponse attendue de l'expert : demande de vérification + délai convenu (réglage du serveur)."""
    from datetime import timedelta

    from django.conf import settings

    requested = formula.review_requested_at or formula.updated_at
    return requested + timedelta(hours=settings.FORMULA_REVIEW_DEADLINE_HOURS)


def rule_formula_to_review(farm, params, today):
    from django.conf import settings

    from formulations.models import FormulaStatus

    hours = settings.FORMULA_REVIEW_DEADLINE_HOURS
    for formula in farm.formulas.filter(status=FormulaStatus.PENDING_REVIEW):
        due = review_due(formula)
        due_text = timezone.localtime(due).strftime("%d/%m/%Y à %H:%M")
        trigger = {"formula_id": formula.pk, "due_at": due.isoformat(), "deadline_hours": hours}
        if timezone.now() > due:
            # Délai dépassé : nouvelle alerte (autre clé), plus visible ; les administrateurs sont relancés.
            yield Candidate(
                dedup_key=f"formula_review_overdue:{formula.pk}",
                alert_type=AlertType.FORMULA_TO_REVIEW,
                severity=AlertSeverity.CRITICAL,
                title=f"Vérification en retard : {formula.name}",
                message=(
                    f"Le délai de réponse convenu ({hours} h) est dépassé depuis le {due_text}. "
                    "Les administrateurs de la plateforme ont été relancés. Vous pouvez aussi inviter un "
                    "autre nutritionniste ou zootechnicien, ou utiliser une ration type validée."
                ),
                rule_code="formula_review_overdue",
                trigger_data={**trigger, "overdue": True},
                target=formula,
            )
            continue
        yield Candidate(
            dedup_key=f"formula_review:{formula.pk}",
            alert_type=AlertType.FORMULA_TO_REVIEW,
            title=f"Formule en attente de vérification : {formula.name}",
            message="Cette formule a été soumise à un expert. Elle ne doit pas être considérée comme validée "
            f"tant que l'expert ne s'est pas prononcé. Réponse attendue avant le {due_text}.",
            rule_code="formula_pending_review",
            trigger_data=trigger,
            target=formula,
        )


FARM_RULES = {
    AlertType.WEIGHING_REMINDER: rule_weighing_reminder,
    AlertType.MISSING_DATA: rule_missing_data,
    AlertType.GROWTH_OUT_OF_RANGE: rule_growth_out_of_range,
    AlertType.FOLLOW_UP_REMINDER: rule_follow_up,
    AlertType.FORMULA_TO_REVIEW: rule_formula_to_review,
}


# --- Synchronisation ------------------------------------------------------------------------


def _sync(scope, candidates, alert_types, rules):
    now = timezone.now()
    open_alerts = {
        a.dedup_key: a
        for a in Alert.objects.filter(
            status__in=[AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED], alert_type__in=alert_types, **scope
        )
    }
    closed_by_user = set(
        Alert.objects.filter(
            alert_type__in=alert_types,
            **scope,
            status__in=[AlertStatus.DISMISSED, AlertStatus.RESOLVED],
            resolved_by__isnull=False,
        ).values_list("dedup_key", flat=True)
    )
    seen = set()
    stats = {"created": 0, "updated": 0, "resolved": 0}
    for c in candidates:
        seen.add(c.dedup_key)
        fields = {
            "title": c.title,
            "message": c.message,
            "severity": c.severity,
            "trigger_data": c.trigger_data,
            "rule_code": c.rule_code,
            "due_date": c.due_date,
            "rule": rules.get(c.alert_type),
        }
        if c.dedup_key in open_alerts:
            alert = open_alerts[c.dedup_key]
            changed = [k for k, v in fields.items() if getattr(alert, k) != v]
            if changed:
                for k in changed:
                    setattr(alert, k, fields[k])
                alert.save()
                stats["updated"] += 1
            continue
        if c.dedup_key in closed_by_user:
            continue
        target_kwargs = {}
        if c.target is not None:
            target_kwargs = {
                "content_type": ContentType.objects.get_for_model(c.target),
                "object_id": c.target.pk,
            }
        Alert.objects.create(
            alert_type=c.alert_type, dedup_key=c.dedup_key, **scope, **fields, **target_kwargs
        )
        stats["created"] += 1
    for key, alert in open_alerts.items():
        if key not in seen:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = now
            alert.trigger_data = {**alert.trigger_data, "resolution": "automatique : condition plus remplie"}
            alert.save()
            stats["resolved"] += 1
    return stats


@transaction.atomic
def evaluate_farm(farm, today=None):
    today = today or timezone.localdate()
    candidates, active_types, rules = [], [], {}
    for alert_type, rule_fn in FARM_RULES.items():
        rule, params, active = effective_rule(alert_type, farm)
        rules[alert_type] = rule
        active_types.append(alert_type)
        if active:
            candidates.extend(rule_fn(farm, params, today))
    # Une règle désactivée n'a plus de candidats : ses alertes ouvertes sont résolues automatiquement.
    return _sync({"farm": farm}, candidates, active_types, rules)


def _overdue_reviews_for_admin(admin):
    """Relance des administrateurs : formules réelles dont le délai de vérification convenu est dépassé."""
    from formulations.models import FeedFormula, FormulaStatus

    late = [
        f
        for f in FeedFormula.objects.filter(
            status=FormulaStatus.PENDING_REVIEW, is_demo=False
        ).select_related("farm")
        if timezone.now() > review_due(f)
    ]
    if not late:
        return []
    farms = sorted({f.farm.name for f in late})
    ids = "-".join(str(pk) for pk in sorted(f.pk for f in late))
    return [
        Candidate(
            dedup_key=f"formula_overdue:{admin.pk}:{ids}",
            alert_type=AlertType.FORMULA_TO_REVIEW,
            severity=AlertSeverity.CRITICAL,
            title=f"{len(late)} vérification(s) de ration en retard",
            message=(
                "Délai de réponse dépassé pour : " + ", ".join(farms) + ". "
                "Validez la ou les formules, ou trouvez un autre nutritionniste / zootechnicien."
            ),
            rule_code="formula_review_overdue_admin",
            trigger_data={"formulas": [f.pk for f in late]},
        )
    ]


@transaction.atomic
def evaluate_reviewers():
    """Une alerte par expert / administrateur actif, résumant les données en attente de validation."""
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    from accounts.models import Role
    from governance.models import ValidationStatus
    from growth.models import GrowthMonitoringRange
    from knowledge_base.models import TechnicalDocument
    from nutrition.models import InclusionConstraint, Ingredient, IngredientComposition, NutritionalReference

    pending = {
        "ingrédients": Ingredient.objects.filter(status=ValidationStatus.PENDING, farm__isnull=True).count(),
        "compositions": IngredientComposition.objects.filter(
            status=ValidationStatus.PENDING, ingredient__farm__isnull=True
        ).count(),
        "références nutritionnelles": NutritionalReference.objects.filter(
            status=ValidationStatus.PENDING
        ).count(),
        "contraintes d'incorporation": InclusionConstraint.objects.filter(
            status=ValidationStatus.PENDING
        ).count(),
        "plages de suivi": GrowthMonitoringRange.objects.filter(status=ValidationStatus.PENDING).count(),
        "documents techniques": TechnicalDocument.objects.filter(status=ValidationStatus.PENDING).count(),
    }
    pending = {k: v for k, v in pending.items() if v}
    total = sum(pending.values())
    _, _, active = effective_rule(AlertType.REFERENCE_TO_VALIDATE, None)
    rule = AlertRule.objects.filter(alert_type=AlertType.REFERENCE_TO_VALIDATE, farm__isnull=True).first()
    stats = {"created": 0, "updated": 0, "resolved": 0}
    reviewers = (
        get_user_model()
        .objects.filter(is_active=True)
        .filter(Q(role__in=[Role.EXPERT, Role.ADMIN]) | Q(is_superuser=True))
    )
    for reviewer in reviewers:
        candidates = []
        if total and active:
            detail = ", ".join(f"{n} {label}" for label, n in pending.items())
            candidates.append(
                Candidate(
                    dedup_key=f"pending_validation:{reviewer.pk}:{total}",
                    alert_type=AlertType.REFERENCE_TO_VALIDATE,
                    title=f"{total} donnée(s) de référence en attente de validation",
                    message=(
                        f"En attente : {detail}. "
                        "Elles ne sont pas utilisées dans les calculs tant qu'elles ne sont pas validées."
                    ),
                    rule_code="reference_pending_validation",
                    trigger_data={"pending": pending, "total": total},
                )
            )
        if reviewer.is_platform_admin:
            candidates.extend(_overdue_reviews_for_admin(reviewer))
        result = _sync(
            {"recipient": reviewer, "farm": None},
            candidates,
            [AlertType.REFERENCE_TO_VALIDATE, AlertType.FORMULA_TO_REVIEW],
            {AlertType.REFERENCE_TO_VALIDATE: rule},
        )
        for k in stats:
            stats[k] += result[k]
    return stats


def evaluate_all(today=None):
    from farms.models import Farm

    totals = {"farms": 0, "created": 0, "updated": 0, "resolved": 0}
    for farm in Farm.objects.filter(is_active=True):
        result = evaluate_farm(farm, today)
        totals["farms"] += 1
        for k in ("created", "updated", "resolved"):
            totals[k] += result[k]
    result = evaluate_reviewers()
    for k in ("created", "updated", "resolved"):
        totals[k] += result[k]
    return totals


def refresh_alerts_safely(farm=None, reviewers=False):
    """Réévalue immédiatement après une action métier (soumission, validation…).

    Une erreur de réévaluation est journalisée mais n'empêche jamais l'action elle-même ;
    la commande quotidienne `evaluate_alerts` rattrape alors l'état.
    """
    import logging

    try:
        if farm is not None:
            evaluate_farm(farm)
        if reviewers:
            evaluate_reviewers()
    except Exception:  # pragma: no cover - dépend d'une panne de base de données
        logging.getLogger(__name__).exception("Échec de la réévaluation des alertes")
