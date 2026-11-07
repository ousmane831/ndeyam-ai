"""
Programme linéaire (PuLP / CBC).

Variables : x_i ≥ 0, kg de matière sèche de l'ingrédient i par animal et par jour.

Contraintes (toutes issues des données validées) :
- ingestion :      MSmin ≤ Σ x_i ≤ MSmax
- besoin journalier :     min ≤ Σ x_i · c_ij ≤ max
- teneur de la ration :   min · Σ x_i ≤ Σ x_i · c_ij ≤ max · Σ x_i
- incorporation :         min% · Σ x ≤ Σ_{i∈S} x_i ≤ max% · Σ x
- disponibilité :         x_i ≤ disponible_i (converti en MS)

Objectifs :
- ÉCONOMIQUE : minimiser Σ prix_MS_i · x_i
- ÉQUILIBRÉ : minimiser Σ |apport_j − cible_j| / cible_j  (+ coût normalisé × 10⁻³ si connu)
  La cible est la valeur « cible » de la référence, sinon le milieu de [min, max].

En cas d'infaisabilité, un second programme « élastique » ajoute un écart autorisé sur chaque
contrainte et minimise les écarts : les contraintes qui doivent être relâchées sont celles qui
rendent le problème impossible, et l'écart chiffré est rapporté.
"""

import warnings

import pulp

from .types import Expression, FormulationResult, Mode
from .verify import build_result

TOLERANCE = 1e-6
TIME_LIMIT_SECONDS = 20


def _solver():
    # PULP_CBC_CMD (CBC fourni avec PuLP 3, utilisable hors ligne) est annoncé obsolète pour PuLP 4.
    # PuLP est figé en version 3 dans requirements.txt ; migration vers COIN_CMD prévue avec PuLP 4.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return pulp.PULP_CBC_CMD(msg=False, timeLimit=TIME_LIMIT_SECONDS)


def _var(model, name):
    return model.add_variable(name, lowBound=0)


def _constraint_rows(problem, x):
    """Liste des contraintes sous la forme (clé, libellé, expression, borne_basse, borne_haute, unité)."""
    total = pulp.lpSum(x.values())
    rows = []
    if problem.dm_intake_min_kg is not None or problem.dm_intake_max_kg is not None:
        rows.append(
            (
                "intake",
                "Ingestion de matière sèche",
                total,
                None,
                problem.dm_intake_min_kg,
                problem.dm_intake_max_kg,
                "kg MS/jour",
            )
        )
    for req in problem.requirements:
        n = problem.nutrients[req.nutrient_id]
        supply = pulp.lpSum(x[i.id] * i.composition_per_kg_dm[n.id] for i in problem.ingredients)
        if req.expression == Expression.DAILY_AMOUNT:
            rows.append(
                (
                    f"req:{n.id}:daily",
                    f"{n.code} (apport journalier)",
                    supply,
                    None,
                    req.min_value,
                    req.max_value,
                    n.daily_unit,
                )
            )
        else:
            rows.append(
                (
                    f"req:{n.id}:conc",
                    f"{n.code} (teneur de la ration)",
                    supply,
                    total,
                    req.min_value,
                    req.max_value,
                    n.concentration_unit,
                )
            )
    for k, bound in enumerate(problem.inclusion_bounds):
        part = pulp.lpSum(x[i] for i in bound.ingredient_ids if i in x)
        low = bound.min_pct_dm / 100 if bound.min_pct_dm is not None else None
        high = bound.max_pct_dm / 100 if bound.max_pct_dm is not None else None
        rows.append(
            (f"incl:{k}", f"Incorporation : {bound.label}", part, total, low, high, "fraction de la MS")
        )
    for ing in problem.ingredients:
        if ing.max_as_fed_kg_per_day is not None:
            rows.append(
                (
                    f"avail:{ing.id}",
                    f"Disponibilité : {ing.name}",
                    x[ing.id],
                    None,
                    None,
                    ing.max_as_fed_kg_per_day * ing.dm_fraction,
                    "kg MS/jour",
                )
            )
    return rows


def _add(model, expr, scale, low, high, name, slack_low=None, slack_high=None):
    """Ajoute low·scale ≤ expr ≤ high·scale (scale = 1 ou Σx pour une teneur), avec écarts éventuels."""
    # Attention : une variable PuLP ne doit jamais être testée comme booléen (« slack or 0 » l'ignorerait).
    factor = scale if scale is not None else 1
    if low is not None:
        lhs = expr + slack_low if slack_low is not None else expr
        model += (lhs >= low * factor), f"{name}_min"
    if high is not None:
        lhs = expr - slack_high if slack_high is not None else expr
        model += (lhs <= high * factor), f"{name}_max"


def _targets(problem):
    out = []
    for req in problem.requirements:
        target = req.target_value
        if target is None and req.min_value is not None and req.max_value is not None:
            target = (req.min_value + req.max_value) / 2
        if target is not None and target > 0:
            out.append((req, target))
    return out


def solve(prepared) -> FormulationResult:
    problem = prepared.problem
    model = pulp.LpProblem("formulation", pulp.LpMinimize)
    x = {i.id: _var(model, f"x_{i.id}") for i in problem.ingredients}
    rows = _constraint_rows(problem, x)
    for key, _label, expr, scale, low, high, _unit in rows:
        _add(model, expr, scale, low, high, key.replace(":", "_"))

    cost = pulp.lpSum(x[i.id] * i.price_per_kg_dm for i in problem.ingredients) if prepared.use_cost else None
    if problem.mode == Mode.ECONOMIC:
        model += cost
    else:
        objective = []
        total = pulp.lpSum(x.values())
        for req, target in _targets(problem):
            n = problem.nutrients[req.nutrient_id]
            supply = pulp.lpSum(x[i.id] * i.composition_per_kg_dm[n.id] for i in problem.ingredients)
            dev_pos = _var(model, f"dev_pos_{n.id}_{req.expression}")
            dev_neg = _var(model, f"dev_neg_{n.id}_{req.expression}")
            reference = target if req.expression == Expression.DAILY_AMOUNT else target * total
            model += (supply - reference == dev_pos - dev_neg), f"target_{n.id}_{req.expression}"
            objective.append((dev_pos + dev_neg) * (1.0 / target))
        if cost is not None:
            max_price = max(i.price_per_kg_dm for i in problem.ingredients) or 1
            objective.append(cost * (1e-3 / max_price))
        model += pulp.lpSum(objective) if objective else pulp.lpSum([])

    status = model.solve(_solver())
    status_label = pulp.LpStatus[status]
    if status_label == "Optimal":
        quantities = {i: max(v.value() or 0.0, 0.0) for i, v in x.items()}
        return build_result(prepared, quantities, status_label)
    if status_label == "Infeasible":
        return _diagnose(prepared, status_label)
    result = FormulationResult(
        status="REFUSED",
        mode=problem.mode,
        solver_status=status_label,
        warnings=prepared.warnings,
        excluded_ingredients=prepared.excluded,
    )
    result.refusal_reasons.append(f"Le solveur n'a pas abouti (statut : {status_label}).")
    return result


def _diagnose(prepared, status_label) -> FormulationResult:
    """Programme élastique : identifie les contraintes à relâcher et l'écart minimal nécessaire."""
    problem = prepared.problem
    model = pulp.LpProblem("diagnostic", pulp.LpMinimize)
    x = {i.id: _var(model, f"x_{i.id}") for i in problem.ingredients}
    rows = _constraint_rows(problem, x)
    penalties, slacks = [], {}
    for key, _label, expr, scale, low, high, _unit in rows:
        name = key.replace(":", "_")
        s_low = _var(model, f"s_low_{name}") if low is not None else None
        s_high = _var(model, f"s_high_{name}") if high is not None else None
        _add(model, expr, scale, low, high, name, s_low, s_high)
        weight_low = 1.0 / max(abs(low), 1e-9) if low else 1.0
        weight_high = 1.0 / max(abs(high), 1e-9) if high else 1.0
        if s_low is not None:
            penalties.append(s_low * weight_low)
        if s_high is not None:
            penalties.append(s_high * weight_high)
        slacks[key] = (s_low, s_high)
    model += pulp.lpSum(penalties)
    model.solve(_solver())

    diagnosis = []
    for key, label, _expr, scale, low, high, unit in rows:
        s_low, s_high = slacks[key]
        for side, slack, bound in (("min", s_low, low), ("max", s_high, high)):
            value = slack.value() if slack is not None else 0
            if value and value > TOLERANCE * max(1.0, abs(bound or 1)):
                # Pour une teneur, l'écart est exprimé sur la quantité totale : on le ramène par kg de MS.
                total = sum(v.value() or 0 for v in x.values())
                gap = value / total if scale is not None and total > TOLERANCE else value
                diagnosis.append(
                    {
                        "constraint": label,
                        "key": key,
                        "side": side,
                        "bound": bound,
                        "unit": unit,
                        "gap": round(gap, 4),
                        "explanation": (
                            f"Minimum de {bound} {unit} impossible à atteindre : "
                            f"il manque environ {gap:.4g} {unit}."
                            if side == "min"
                            else f"Maximum de {bound} {unit} impossible à respecter : "
                            f"dépassement d'environ {gap:.4g} {unit}."
                        ),
                    }
                )
    result = FormulationResult(
        status="INFEASIBLE",
        mode=problem.mode,
        solver_status=status_label,
        warnings=prepared.warnings,
        excluded_ingredients=prepared.excluded,
        infeasibility=diagnosis,
    )
    result.refusal_reasons.append(
        "Aucune ration ne permet de respecter simultanément toutes les contraintes "
        "avec les ingrédients proposés. "
        "Ajoutez des ingrédients, vérifiez les disponibilités ou faites revoir les contraintes par un expert."
    )
    return result
