"""
Construction et vérification INDÉPENDANTE du résultat.

Les apports et le respect de chaque contrainte sont recalculés à partir des quantités trouvées,
sans se fier aux variables du solveur. Une ration n'est jamais présentée comme conforme si une
contrainte n'est pas vérifiée par ce recalcul.
"""

from .types import Expression, FormulationResult

REL_TOLERANCE = 1e-4  # 0,01 % : arrondis numériques du solveur


def _within(value, low, high):
    def ok_low():
        return low is None or value >= low - REL_TOLERANCE * max(1.0, abs(low))

    def ok_high():
        return high is None or value <= high + REL_TOLERANCE * max(1.0, abs(high))

    if not ok_low():
        return "below"
    if not ok_high():
        return "above"
    return "ok"


def _expression_label(expression):
    return "apport journalier" if expression == Expression.DAILY_AMOUNT else "teneur"


def build_result(prepared, quantities_dm, solver_status) -> FormulationResult:
    problem = prepared.problem
    ingredients = {i.id: i for i in problem.ingredients}
    total_dm = sum(quantities_dm.values())
    used = {i: q for i, q in quantities_dm.items() if q > 1e-9}
    total_as_fed = sum(q / ingredients[i].dm_fraction for i, q in used.items())

    items, total_cost = [], 0.0
    for ing_id, q_dm in sorted(used.items(), key=lambda kv: -kv[1]):
        ing = ingredients[ing_id]
        q_af = q_dm / ing.dm_fraction
        cost = q_af * ing.price_per_kg_as_fed if prepared.use_cost else None
        total_cost += cost or 0.0
        items.append(
            {
                "ingredient_id": ing_id,
                "name": ing.name,
                "inclusion_pct_dm": 100 * q_dm / total_dm if total_dm else 0.0,
                "inclusion_pct_as_fed": 100 * q_af / total_as_fed if total_as_fed else 0.0,
                "quantity_dm_kg": q_dm,
                "quantity_as_fed_kg": q_af,
                "price_per_kg_as_fed": ing.price_per_kg_as_fed,
                "cost_per_day": cost,
            }
        )

    # Apports estimés pour chaque nutriment connu de TOUS les ingrédients utilisés.
    nutrient_rows = []
    requirement_by_nutrient = {}
    for req in problem.requirements:
        requirement_by_nutrient.setdefault(req.nutrient_id, []).append(req)
    candidate_ids = (
        set().union(*(ingredients[i].composition_per_kg_dm.keys() for i in used)) if used else set()
    )
    for n_id in sorted(
        candidate_ids | set(requirement_by_nutrient),
        key=lambda n: problem.nutrients[n].code if n in problem.nutrients else "",
    ):
        if n_id not in problem.nutrients:
            continue
        n = problem.nutrients[n_id]
        missing = [ingredients[i].name for i in used if n_id not in ingredients[i].composition_per_kg_dm]
        daily = (
            None if missing else sum(q * ingredients[i].composition_per_kg_dm[n_id] for i, q in used.items())
        )
        row = {
            "nutrient_id": n_id,
            "code": n.code,
            "name": n.name,
            "system": n.system,
            "daily_amount": daily,
            "daily_unit": n.daily_unit,
            "concentration_dm": (daily / total_dm) if daily is not None and total_dm else None,
            "concentration_unit": n.concentration_unit,
            "complete": not missing,
            "missing_for": missing,
            "requirements": [],
        }
        for req in requirement_by_nutrient.get(n_id, []):
            value = (
                row["daily_amount"] if req.expression == Expression.DAILY_AMOUNT else row["concentration_dm"]
            )
            row["requirements"].append(
                {
                    "expression": req.expression,
                    "min": req.min_value,
                    "target": req.target_value,
                    "max": req.max_value,
                    "unit": n.daily_unit
                    if req.expression == Expression.DAILY_AMOUNT
                    else n.concentration_unit,
                    "status": _within(value, req.min_value, req.max_value)
                    if value is not None
                    else "unknown",
                }
            )
        nutrient_rows.append(row)

    constraints = []
    if problem.dm_intake_min_kg is not None or problem.dm_intake_max_kg is not None:
        constraints.append(
            {
                "constraint": "Ingestion de matière sèche",
                "value": total_dm,
                "unit": "kg MS/jour",
                "min": problem.dm_intake_min_kg,
                "max": problem.dm_intake_max_kg,
                "status": _within(total_dm, problem.dm_intake_min_kg, problem.dm_intake_max_kg),
            }
        )
    for row in nutrient_rows:
        for req in row["requirements"]:
            value = (
                row["daily_amount"]
                if req["expression"] == Expression.DAILY_AMOUNT
                else row["concentration_dm"]
            )
            constraints.append(
                {
                    "constraint": f"{row['code']} ({_expression_label(req['expression'])})",
                    "value": value,
                    "unit": req["unit"],
                    "min": req["min"],
                    "max": req["max"],
                    "status": req["status"],
                }
            )
    for bound in problem.inclusion_bounds:
        share = 100 * sum(used.get(i, 0) for i in bound.ingredient_ids) / total_dm if total_dm else 0
        constraints.append(
            {
                "constraint": f"Incorporation : {bound.label}",
                "value": share,
                "unit": "% MS",
                "min": bound.min_pct_dm,
                "max": bound.max_pct_dm,
                "status": _within(share, bound.min_pct_dm, bound.max_pct_dm),
            }
        )
    for ing in problem.ingredients:
        if ing.max_as_fed_kg_per_day is not None:
            q_af = used.get(ing.id, 0) / ing.dm_fraction
            constraints.append(
                {
                    "constraint": f"Disponibilité : {ing.name}",
                    "value": q_af,
                    "unit": "kg brut/jour",
                    "min": None,
                    "max": ing.max_as_fed_kg_per_day,
                    "status": _within(q_af, None, ing.max_as_fed_kg_per_day),
                }
            )

    warnings = list(prepared.warnings)
    all_ok = all(c["status"] == "ok" for c in constraints)
    if not all_ok:
        warnings.append(
            "Le recalcul indépendant révèle une contrainte non respectée : la ration n'est pas conforme."
        )

    sources = {problem.reference_source} if problem.reference_source else set()
    for i in used:
        sources |= set(ingredients[i].sources.values())
    sources |= {b.source for b in problem.inclusion_bounds if b.source}

    return FormulationResult(
        status="ESTIMATED" if all_ok else "INFEASIBLE",
        mode=problem.mode,
        solver_status=solver_status,
        items=items,
        dm_intake_kg_day=total_dm,
        as_fed_kg_day=total_as_fed,
        cost_per_day=total_cost if prepared.use_cost else None,
        cost_per_kg_as_fed=(total_cost / total_as_fed) if prepared.use_cost and total_as_fed else None,
        currency=next((i.currency for i in problem.ingredients), "XOF"),
        nutrients=nutrient_rows,
        constraints=constraints,
        warnings=warnings,
        excluded_ingredients=prepared.excluded,
        sources=sorted(s for s in sources if s),
    )
