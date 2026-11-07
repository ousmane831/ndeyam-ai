"""
Moteur de formulation des aliments de NDEYAM AI.

Paquet Python pur (aucune dépendance à Django) : il reçoit un `Problem` entièrement décrit
et renvoie un `FormulationResult`. Il ne lit aucune donnée par lui-même et n'invente rien :
tout nutriment, besoin ou composition absent de l'entrée est considéré comme inconnu.

    Problem ──▶ checks.prepare()  ──▶ refus motivé, ou problème nettoyé + avertissements
             ──▶ solver.solve()   ──▶ programme linéaire (PuLP / CBC)
             ──▶ verify.verify()  ──▶ recalcul indépendant des apports et des contraintes

Le résultat est une ESTIMATION MATHÉMATIQUE : il ne devient une recommandation qu'après
validation par un expert.
"""

from .types import (  # noqa: F401
    ENGINE_VERSION,
    FormulationResult,
    InclusionBound,
    IngredientInput,
    Mode,
    NutrientSpec,
    Problem,
    RequirementSpec,
)


def formulate(problem):
    from .checks import prepare
    from .solver import solve

    prepared = prepare(problem)
    if prepared.refused:
        return prepared.as_refusal()
    return solve(prepared)
