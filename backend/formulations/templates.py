"""
Rations types validées : recherche des rations types applicables à un profil d'animaux, et application
immédiate.

Une ration type fixe la part de chaque aliment dans la matière sèche (MS) et la MS journalière par animal,
pour une tranche de poids : c'est cela que l'expert a validé. L'appliquer ne recalcule que des conversions,
avec les données de l'exploitation : MS validée de chaque aliment (kg brut = kg MS / teneur en MS) et prix
du jour (prix habituel de la saison en priorité, comme le calcul). Les apports nutritionnels restent ceux
validés.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from governance.models import ValidationStatus
from nutrition.models import IngredientComposition, IngredientPrice, NutrientCategory

from .models import (
    FeedFormula,
    FeedFormulaIngredient,
    FormulaMode,
    FormulaStatus,
    RationTemplate,
    RationTemplateItem,
)


class TemplateError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def template_pool(demo):
    qs = RationTemplate.objects.select_related("validated_by", "source").prefetch_related("items__ingredient")
    if demo:
        return qs.filter(is_demo=True).exclude(status=ValidationStatus.REJECTED)
    return qs.filter(is_demo=False, status=ValidationStatus.VALIDATED)


def _fits(value, wanted):
    """Critère de la ration type vide : tous les profils ; sinon il doit correspondre exactement."""
    return wanted is None or (value is not None and getattr(value, "pk", value) == wanted)


def matching_templates(farm, profile, season=None):
    """Rations types utilisables pour ce profil (espèce, catégorie, stade, objectif, poids, saison)."""
    weight = profile.get("weight_kg")
    out = []
    for template in template_pool(farm.is_demo).filter(species=profile.get("species")):
        if not (
            _fits(profile.get("category"), template.category_id)
            and _fits(profile.get("physiological_stage"), template.physiological_stage_id)
            and _fits(profile.get("objective"), template.objective_id)
            and _fits(season, template.season_id)
        ):
            continue
        if weight is None or not (template.weight_min_kg <= Decimal(weight) <= template.weight_max_kg):
            continue
        if any(item.ingredient.farm_id not in (None, farm.pk) for item in template.items.all()):
            continue
        out.append(template)
    return out


def _dry_matter(farm, ingredient):
    comps = IngredientComposition.objects.filter(
        ingredient=ingredient, nutrient__category=NutrientCategory.DRY_MATTER
    )
    comps = (
        comps.filter(is_demo=True).exclude(status=ValidationStatus.REJECTED)
        if farm.is_demo
        else comps.usable_for_engine()
    )
    comp = comps.order_by("-status", "-updated_at").first()
    return Decimal(comp.value) / Decimal(1000) if comp and comp.value else None


def _price(farm, ingredient, season):
    qs = IngredientPrice.objects.filter(
        farm=farm, ingredient=ingredient, valid_from__lte=timezone.localdate(), is_demo=farm.is_demo
    )
    if season is not None:
        seasonal = qs.filter(season=season).order_by("-valid_from", "-created_at").first()
        if seasonal:
            return seasonal
    return qs.filter(season__isnull=True).order_by("-valid_from", "-created_at").first()


def _pk(value):
    return getattr(value, "pk", value)


def _q(value, places):
    return Decimal(value).quantize(Decimal(places), rounding=ROUND_HALF_UP)


@transaction.atomic
def apply_template(template, *, farm, user, profile, group=None, animal=None, name="", season=None):
    """Crée la formule de la ration type pour cette exploitation (validée d'emblée, sauf DEMO)."""
    if template.is_demo != farm.is_demo:
        raise TemplateError("Une ration type DEMO ne s'applique qu'à une exploitation DEMO, et inversement.")
    if template not in matching_templates(farm, profile, getattr(season, "pk", season)):
        raise TemplateError(
            "Cette ration type ne correspond pas au profil de ces animaux (espèce, catégorie, stade, "
            "objectif, saison ou tranche de poids)."
        )
    rows, missing = [], []
    for item in template.items.all():
        dm = _dry_matter(farm, item.ingredient)
        if not dm:
            missing.append(item.ingredient.name)
            continue
        rows.append((item, dm, _price(farm, item.ingredient, season)))
    if missing:
        raise TemplateError(
            "Teneur en matière sèche validée inconnue pour : "
            + ", ".join(missing)
            + ". La ration type ne peut "
            "pas être convertie en quantités pour cette exploitation."
        )

    intake = Decimal(template.dm_intake_kg_day)
    total_as_fed = sum(intake * Decimal(item.inclusion_pct_dm) / 100 / dm for item, dm, _p in rows)
    cost_known = all(price is not None for _i, _d, price in rows)
    validated = not farm.is_demo
    formula = FeedFormula.objects.create(
        farm=farm,
        name=name or template.name,
        species=template.species,
        mode=FormulaMode.TEMPLATE,
        status=FormulaStatus.VALIDATED if validated else FormulaStatus.ESTIMATED,
        is_demo=farm.is_demo,
        animal=animal,
        group=group,
        season=season,
        template=template,
        animal_weight_kg=profile.get("weight_kg"),
        # Le profil contient des objets (lot) ou des identifiants (requête) : on n'enregistre que les clés.
        physiological_stage_id=_pk(profile.get("physiological_stage")),
        objective_id=_pk(profile.get("objective")),
        dm_intake_kg_day=_q(intake, "0.001"),
        as_fed_kg_day=_q(total_as_fed, "0.001"),
        currency="XOF",
        validated_by=template.validated_by if validated else None,
        validated_at=(template.validated_at or timezone.now()) if validated else None,
        review_comment=(
            f"Ration type validée « {template.name} »" if validated else "Ration type DEMO (jamais validée)."
        ),
        result_snapshot={
            "kind": "ration_template",
            "template": {"id": template.pk, "name": template.name},
            "profile": {"head_count": profile.get("head_count")},
            "season": {"id": season.pk, "name": season.name, "is_hot": season.is_hot} if season else None,
            "sources": [str(template.source)] if template.source_id else [],
        },
        warnings=[] if cost_known else ["Certains prix sont inconnus : le coût n'est pas calculé."],
        created_by=user,
    )
    total_cost = Decimal(0)
    for item, dm, price in rows:
        q_dm = intake * Decimal(item.inclusion_pct_dm) / 100
        q_af = q_dm / dm
        cost = q_af * price.price_per_kg_as_fed if price else None
        total_cost += cost or 0
        FeedFormulaIngredient.objects.create(
            formula=formula,
            ingredient=item.ingredient,
            inclusion_pct_dm=_q(item.inclusion_pct_dm, "0.001"),
            inclusion_pct_as_fed=_q(100 * q_af / total_as_fed, "0.001"),
            quantity_dm_kg=_q(q_dm, "0.0001"),
            quantity_as_fed_kg=_q(q_af, "0.0001"),
            price=price,
            price_per_kg_as_fed=price.price_per_kg_as_fed if price else None,
            cost_per_day=_q(cost, "0.01") if cost is not None else None,
        )
    if cost_known:
        formula.cost_per_day = _q(total_cost, "0.01")
        formula.cost_per_kg_as_fed = _q(total_cost / total_as_fed, "0.01")
        formula.save(update_fields=["cost_per_day", "cost_per_kg_as_fed"])
    return formula


def template_from_formula(formula, *, user, name, weight_min_kg, weight_max_kg, conditions=""):
    """Brouillon de ration type à partir d'une formule validée (à valider ensuite par un expert)."""
    items = [i for i in formula.items.all() if i.inclusion_pct_dm]
    if formula.status != FormulaStatus.VALIDATED and not formula.is_demo:
        raise TemplateError("Seule une formule validée par un expert peut devenir une ration type.")
    if not items or not formula.dm_intake_kg_day:
        raise TemplateError("La formule doit indiquer la matière sèche de chaque aliment et l'ingestion.")
    profile = formula.result_snapshot.get("profile") or {}
    template = RationTemplate.objects.create(
        name=name,
        species=formula.species,
        category_id=profile.get("category"),
        physiological_stage=formula.physiological_stage,
        objective=formula.objective,
        season=formula.season,
        weight_min_kg=weight_min_kg,
        weight_max_kg=weight_max_kg,
        dm_intake_kg_day=formula.dm_intake_kg_day,
        conditions=conditions,
        origin_formula=formula,
        source=formula.reference.source if formula.reference_id else None,
        is_demo=formula.is_demo,
        created_by=user,
    )
    for item in items:
        RationTemplateItem.objects.create(
            template=template, ingredient=item.ingredient, inclusion_pct_dm=item.inclusion_pct_dm
        )
    return template
