"""
Pont entre la base de données et le moteur de formulation (`formulations.engine`).

Sélection stricte des données :
- exploitation RÉELLE : uniquement des données VALIDÉES et non DEMO (référence, compositions,
  contraintes d'incorporation) et des prix non DEMO ;
- exploitation DEMO : uniquement des données DEMO, jamais mélangées à des données réelles ;
  la formule produite est marquée DEMO et ne peut pas être validée (contrainte en base).
- seuls les nutriments universels et ceux du système de la référence sont utilisés.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from governance.models import ValidationStatus
from nutrition.models import (
    InclusionConstraint,
    IngredientComposition,
    IngredientPrice,
    NutrientCategory,
    NutritionalReference,
)

from .engine import InclusionBound, IngredientInput, Mode, NutrientSpec, Problem, RequirementSpec, formulate
from .engine.types import Expression
from .models import FeedFormula, FeedFormulaIngredient, FormulaStatus


def _reference_pool(demo):
    if demo:
        return NutritionalReference.objects.filter(is_demo=True).exclude(status=ValidationStatus.REJECTED)
    return NutritionalReference.objects.usable_for_engine()


def match_reference(
    *,
    species,
    demo=False,
    breed=None,
    category=None,
    stage=None,
    objective=None,
    weight_kg=None,
    age_months=None,
):
    """Référence la plus spécifique applicable au profil. Une borne de poids ou d'âge exige la donnée."""
    qs = _reference_pool(demo).filter(species=species)
    for field, value in (
        ("breed", breed),
        ("category", category),
        ("physiological_stage", stage),
        ("objective", objective),
    ):
        qs = (
            qs.filter(Q(**{f"{field}__isnull": True}) | Q(**{field: value}))
            if value
            else qs.filter(**{f"{field}__isnull": True})
        )
    if weight_kg is None:
        qs = qs.filter(weight_min_kg__isnull=True, weight_max_kg__isnull=True)
    else:
        qs = qs.filter(Q(weight_min_kg__isnull=True) | Q(weight_min_kg__lte=weight_kg))
        qs = qs.filter(Q(weight_max_kg__isnull=True) | Q(weight_max_kg__gte=weight_kg))
    if age_months is None:
        qs = qs.filter(age_min_months__isnull=True, age_max_months__isnull=True)
    else:
        qs = qs.filter(Q(age_min_months__isnull=True) | Q(age_min_months__lte=age_months))
        qs = qs.filter(Q(age_max_months__isnull=True) | Q(age_max_months__gte=age_months))

    def specificity(ref):
        return sum(
            v is not None
            for v in (
                ref.breed_id,
                ref.category_id,
                ref.physiological_stage_id,
                ref.objective_id,
                ref.weight_min_kg,
                ref.weight_max_kg,
                ref.age_min_months,
                ref.age_max_months,
            )
        )

    candidates = sorted(qs.select_related("system", "source"), key=lambda r: (-specificity(r), -r.pk))
    return candidates[0] if candidates else None


def _float(value):
    return float(value) if value is not None else None


def build_problem(*, farm, reference, mode, entries, number_of_animals=None, duration_days=None):
    """`entries` : liste de dicts {ingredient, price_per_kg_as_fed?, available_kg_as_fed?}."""
    demo = farm.is_demo
    warnings = []
    allowed_system = reference.system_id

    requirements, nutrients = [], {}
    for req in reference.requirements.select_related("nutrient__system"):
        n = req.nutrient
        nutrients[n.pk] = NutrientSpec(
            n.pk, n.code, n.name, n.amount_unit, n.system.code if n.system else None
        )
        requirements.append(
            RequirementSpec(
                n.pk,
                Expression(req.expression),
                _float(req.min_value),
                _float(req.target_value),
                _float(req.max_value),
            )
        )

    ingredient_ids = [e["ingredient"].pk for e in entries]
    comps = (
        IngredientComposition.objects.filter(ingredient_id__in=ingredient_ids)
        .filter(Q(nutrient__system__isnull=True) | Q(nutrient__system_id=allowed_system))
        .select_related("nutrient__system", "source")
    )
    comps = (
        comps.filter(is_demo=True).exclude(status=ValidationStatus.REJECTED)
        if demo
        else comps.usable_for_engine()
    )
    by_ingredient = {}
    for comp in comps.order_by("ingredient_id", "nutrient_id", "-status", "-updated_at"):
        bucket = by_ingredient.setdefault(comp.ingredient_id, {})
        bucket.setdefault(comp.nutrient_id, comp)  # une seule valeur par nutriment (validée en priorité)

    prices = {}
    price_qs = IngredientPrice.objects.filter(
        farm=farm, ingredient_id__in=ingredient_ids, valid_from__lte=timezone.localdate(), is_demo=demo
    )
    for price in price_qs.order_by("ingredient_id", "-valid_from", "-created_at"):
        prices.setdefault(price.ingredient_id, price)

    ingredients = []
    for entry in entries:
        ing = entry["ingredient"]
        if ing.is_demo != demo:
            warnings.append(
                f"« {ing.name} » exclu : "
                + (
                    "donnée DEMO interdite dans une exploitation réelle."
                    if not demo
                    else "seules des données DEMO sont utilisées dans une exploitation DEMO."
                )
            )
            continue
        ing_comps = by_ingredient.get(ing.pk, {})
        dm = next((c for c in ing_comps.values() if c.nutrient.category == NutrientCategory.DRY_MATTER), None)
        composition, sources = {}, {}
        for n_id, comp in ing_comps.items():
            if comp.nutrient.category == NutrientCategory.DRY_MATTER:
                continue
            composition[n_id] = float(comp.value)
            sources[n_id] = str(comp.source) if comp.source_id else "Source non renseignée (DEMO)"
            if n_id not in nutrients:
                n = comp.nutrient
                nutrients[n_id] = NutrientSpec(
                    n.pk, n.code, n.name, n.amount_unit, n.system.code if n.system else None
                )
        if dm is not None and dm.source_id:
            sources[dm.nutrient_id] = str(dm.source)

        price_value, currency, price_is_demo = entry.get("price_per_kg_as_fed"), "XOF", demo
        if price_value is None and ing.pk in prices:
            price_value, currency = prices[ing.pk].price_per_kg_as_fed, prices[ing.pk].currency
        elif price_value is not None:
            warnings.append(f"Prix de « {ing.name} » saisi pour ce calcul ({price_value} par kg brut).")

        available = entry.get("available_kg_as_fed")
        per_day = None
        if available is not None:
            per_day = float(available) / (number_of_animals * duration_days)
        ingredients.append(
            IngredientInput(
                id=ing.pk,
                name=ing.name,
                dm_g_per_kg_as_fed=_float(dm.value) if dm else None,
                composition_per_kg_dm=composition,
                price_per_kg_as_fed=_float(price_value),
                currency=currency,
                max_as_fed_kg_per_day=per_day,
                sources=sources,
                price_is_demo=price_is_demo and demo,
            )
        )

    bounds_qs = (
        InclusionConstraint.objects.filter(species=reference.species)
        .filter(Q(animal_category__isnull=True) | Q(animal_category=reference.category_id))
        .select_related("ingredient", "ingredient_category", "source")
    )
    bounds_qs = (
        bounds_qs.filter(is_demo=True).exclude(status=ValidationStatus.REJECTED)
        if demo
        else bounds_qs.usable_for_engine()
    )
    bounds = []
    for c in bounds_qs:
        if c.ingredient_id:
            ids = frozenset({c.ingredient_id}) & frozenset(ingredient_ids)
        else:
            ids = frozenset(
                e["ingredient"].pk for e in entries if e["ingredient"].category_id == c.ingredient_category_id
            )
        if ids:
            bounds.append(
                InclusionBound(
                    str(c.ingredient or c.ingredient_category),
                    ids,
                    _float(c.min_pct_dm),
                    _float(c.max_pct_dm),
                    str(c.source) if c.source_id else "",
                )
            )

    problem = Problem(
        mode=Mode(mode),
        nutrients=nutrients,
        requirements=requirements,
        ingredients=ingredients,
        dm_intake_min_kg=_float(reference.dm_intake_min_kg_day),
        dm_intake_max_kg=_float(reference.dm_intake_max_kg_day),
        inclusion_bounds=bounds,
        reference_label=str(reference),
        reference_source=str(reference.source) if reference.source_id else "",
        is_demo=demo,
    )
    return problem, warnings, prices


def _d(value, places="0.0001"):
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _rounded(obj):
    if isinstance(obj, float):
        return round(obj, 6)
    if isinstance(obj, dict):
        return {k: _rounded(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_rounded(v) for v in obj]
    return obj


STATUS_MAP = {
    "ESTIMATED": FormulaStatus.ESTIMATED,
    "INFEASIBLE": FormulaStatus.INFEASIBLE,
    "REFUSED": FormulaStatus.REFUSED,
}


def run_formulation(
    *,
    farm,
    user,
    name,
    species,
    mode,
    entries,
    reference=None,
    profile=None,
    number_of_animals=None,
    duration_days=None,
    animal=None,
    group=None,
    notes="",
    save=True,
):
    profile = profile or {}
    pre_warnings = []
    if reference is None:
        reference = match_reference(
            species=species,
            demo=farm.is_demo,
            breed=profile.get("breed"),
            category=profile.get("category"),
            stage=profile.get("physiological_stage"),
            objective=profile.get("objective"),
            weight_kg=profile.get("weight_kg"),
            age_months=profile.get("age_months"),
        )
        if reference is not None:
            pre_warnings.append(f"Référence retenue automatiquement : « {reference.name} ».")

    if reference is None:
        result = {
            "status": "REFUSED",
            "mode": mode,
            "solver_status": "non lancé",
            "items": [],
            "nutrients": [],
            "constraints": [],
            "infeasibility": [],
            "excluded_ingredients": [],
            "sources": [],
            "warnings": [],
            "refusal_reasons": [
                "Aucune référence nutritionnelle validée ne correspond à ce profil d'animal "
                "(espèce, catégorie, stade, objectif, poids, âge). "
                "Un expert doit d'abord saisir et valider une "
                "référence sourcée."
                if not farm.is_demo
                else "Aucune référence DEMO ne correspond à ce profil."
            ],
        }
        problem_prices = {}
    else:
        problem, warnings, problem_prices = build_problem(
            farm=farm,
            reference=reference,
            mode=mode,
            entries=entries,
            number_of_animals=number_of_animals,
            duration_days=duration_days,
        )
        result = formulate(problem).to_dict()
        result["warnings"] = pre_warnings + warnings + result["warnings"]

    result["reference"] = (
        {
            "id": reference.pk,
            "name": reference.name,
            "system": reference.system.code,
            "source": str(reference.source) if reference.source_id else None,
            "status": reference.status,
            "is_demo": reference.is_demo,
        }
        if reference
        else None
    )
    result["profile"] = {
        k: (getattr(v, "pk", v) if not isinstance(v, Decimal) else str(v)) for k, v in profile.items()
    }
    if farm.is_demo:
        result["warnings"].insert(
            0,
            "Calcul de DÉMONSTRATION réalisé avec des données fictives : "
            "ne pas utiliser pour nourrir des animaux.",
        )
    result = _rounded(result)
    if not save:
        return None, result

    with transaction.atomic():
        formula = FeedFormula.objects.create(
            farm=farm,
            name=name,
            species=species,
            reference=reference,
            mode=mode,
            status=STATUS_MAP[result["status"]],
            is_demo=farm.is_demo,
            animal=animal,
            group=group,
            animal_weight_kg=profile.get("weight_kg"),
            animal_age_months=profile.get("age_months"),
            physiological_stage=profile.get("physiological_stage"),
            objective=profile.get("objective"),
            dm_intake_kg_day=_d(result.get("dm_intake_kg_day"), "0.001"),
            as_fed_kg_day=_d(result.get("as_fed_kg_day"), "0.001"),
            cost_per_day=_d(result.get("cost_per_day"), "0.01"),
            cost_per_kg_as_fed=_d(result.get("cost_per_kg_as_fed"), "0.01"),
            currency=result.get("currency", "XOF"),
            result_snapshot=result,
            warnings=result["warnings"],
            solver_status=result.get("solver_status", ""),
            engine_version=result.get("engine_version", ""),
            notes=notes,
            created_by=user,
        )
        for item in result["items"]:
            price = problem_prices.get(item["ingredient_id"])
            FeedFormulaIngredient.objects.create(
                formula=formula,
                ingredient_id=item["ingredient_id"],
                inclusion_pct_dm=_d(item["inclusion_pct_dm"], "0.001"),
                inclusion_pct_as_fed=_d(item["inclusion_pct_as_fed"], "0.001"),
                quantity_dm_kg=_d(item["quantity_dm_kg"]),
                quantity_as_fed_kg=_d(item["quantity_as_fed_kg"]),
                price=price
                if price and item["price_per_kg_as_fed"] == float(price.price_per_kg_as_fed)
                else None,
                price_per_kg_as_fed=_d(item["price_per_kg_as_fed"], "0.01"),
                cost_per_day=_d(item["cost_per_day"], "0.01"),
            )
    return formula, result
