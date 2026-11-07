"""
Analyse d'une ration composée de quantités brutes (formule saisie manuellement).

Ce module ne fait QUE de l'arithmétique sur des données VALIDÉES (non DEMO) :
- matière sèche apportée par chaque ingrédient (teneur en MS validée) ;
- apports estimés par nutriment (somme quantité de MS × teneur validée) ;
- coût à partir du dernier prix connu de l'exploitation.

Il ne fabrique aucune valeur : un ingrédient sans teneur validée rend l'apport du nutriment
« incomplet » et l'ingrédient est cité. Le résultat est une estimation, jamais une recommandation.
Ce n'est pas le moteur d'optimisation (étape 6) : aucune contrainte n'est résolue ici.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from nutrition.models import IngredientComposition, IngredientPrice, NutrientCategory

Q4 = Decimal("0.0001")
Q2 = Decimal("0.01")


def _q(value, quantum=Q4):
    return value.quantize(quantum, rounding=ROUND_HALF_UP) if value is not None else None


def latest_prices(farm, ingredients, on_date=None):
    on_date = on_date or timezone.localdate()
    prices = {}
    qs = (
        IngredientPrice.objects.filter(farm=farm, ingredient__in=ingredients, valid_from__lte=on_date)
        .order_by("ingredient_id", "-valid_from", "-created_at")
        .distinct("ingredient_id")
    )
    for price in qs:
        prices[price.ingredient_id] = price
    return prices


def analyse_ration(farm, items, system=None):
    """
    `items` : liste de (Ingredient, quantité brute en kg par animal et par jour).
    `system` : NutritionSystem facultatif ; s'il est fourni, seuls les nutriments universels et ceux
    de ce système sont calculés (jamais de mélange).
    """
    ingredients = [ing for ing, _ in items]
    compositions = (
        IngredientComposition.objects.usable_for_engine()
        .filter(ingredient__in=ingredients)
        .select_related("nutrient__system", "source")
    )
    if system is not None:
        compositions = compositions.filter(nutrient__system__in=[system]) | compositions.filter(
            nutrient__system=None
        )
    by_ingredient = {}
    nutrients = {}
    sources = {}
    for comp in compositions:
        by_ingredient.setdefault(comp.ingredient_id, {})[comp.nutrient_id] = comp
        nutrients[comp.nutrient_id] = comp.nutrient
        sources[comp.source_id] = str(comp.source)

    prices = latest_prices(farm, ingredients)
    warnings = []
    lines = []
    total_as_fed = Decimal("0")
    total_dm = Decimal("0")
    dm_complete = True
    total_cost = Decimal("0")
    cost_complete = True

    for ingredient, qty in items:
        qty = Decimal(str(qty))
        total_as_fed += qty
        comps = by_ingredient.get(ingredient.pk, {})
        dm_comp = next(
            (c for c in comps.values() if c.nutrient.category == NutrientCategory.DRY_MATTER), None
        )
        qty_dm = qty * dm_comp.value / Decimal("1000") if dm_comp else None
        if qty_dm is None:
            dm_complete = False
            warnings.append(f"Matière sèche de « {ingredient.name} » inconnue (aucune valeur validée).")
        else:
            total_dm += qty_dm
        price = prices.get(ingredient.pk)
        cost = qty * price.price_per_kg_as_fed if price else None
        if price is None:
            cost_complete = False
            warnings.append(f"Aucun prix enregistré pour « {ingredient.name} » dans cette exploitation.")
        else:
            total_cost += cost
            if price.is_demo:
                warnings.append(f"Le prix de « {ingredient.name} » est une donnée DEMO.")
        lines.append(
            {
                "ingredient": ingredient,
                "quantity_as_fed_kg": qty,
                "quantity_dm_kg": qty_dm,
                "price": price,
                "cost": cost,
            }
        )

    for line in lines:
        line["inclusion_pct_as_fed"] = (
            (line["quantity_as_fed_kg"] / total_as_fed * 100) if total_as_fed else None
        )
        line["inclusion_pct_dm"] = (
            line["quantity_dm_kg"] / total_dm * 100
            if dm_complete and total_dm and line["quantity_dm_kg"] is not None
            else None
        )

    nutrient_rows = []
    for nutrient in sorted(nutrients.values(), key=lambda n: (n.sort_order, n.code)):
        if nutrient.category == NutrientCategory.DRY_MATTER:
            continue
        total = Decimal("0")
        missing = []
        for line in lines:
            comp = by_ingredient.get(line["ingredient"].pk, {}).get(nutrient.pk)
            if comp is None or line["quantity_dm_kg"] is None:
                missing.append(line["ingredient"].name)
            else:
                total += line["quantity_dm_kg"] * comp.value
        complete = not missing
        nutrient_rows.append(
            {
                "nutrient_id": nutrient.pk,
                "code": nutrient.code,
                "name": nutrient.name,
                "system": nutrient.system.code if nutrient.system else None,
                "daily_amount": str(_q(total)) if complete else None,
                "daily_unit": f"{nutrient.amount_unit}/jour",
                "concentration_dm": str(_q(total / total_dm))
                if complete and dm_complete and total_dm
                else None,
                "concentration_unit": nutrient.unit_label,
                "complete": complete,
                "missing_for": missing,
            }
        )

    return {
        "lines": lines,
        "total_as_fed_kg": _q(total_as_fed),
        "total_dm_kg": _q(total_dm) if dm_complete else None,
        "cost_per_day": _q(total_cost, Q2) if cost_complete else None,
        "cost_per_kg_as_fed": _q(total_cost / total_as_fed, Q2) if cost_complete and total_as_fed else None,
        "currency": next((line["price"].currency for line in lines if line["price"]), "XOF"),
        "nutrients": nutrient_rows,
        "sources": sorted(set(sources.values())),
        "warnings": warnings,
        "disclaimer": (
            "Apports estimés à partir des seules compositions validées. "
            "Il ne s'agit pas d'une recommandation nutritionnelle validée."
        ),
    }
