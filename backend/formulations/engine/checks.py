"""
Contrôles préalables : le moteur REFUSE de calculer quand les données essentielles manquent.

Refus (aucun calcul) :
- aucun besoin nutritionnel ;
- ingestion de matière sèche non renseignée ;
- aucun ingrédient utilisable.

Exclusions d'ingrédients (avec avertissement, jamais de valeur supposée) :
- teneur en MS inconnue (aucune conversion brut ↔ MS possible) ;
- valeur inconnue pour un nutriment soumis à contrainte (la traiter comme zéro serait une invention) ;
- prix inconnu en mode économique.
"""

from dataclasses import dataclass, field

from .types import FormulationResult, Mode, Problem


@dataclass
class Prepared:
    problem: Problem
    refused: bool = False
    refusal_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    use_cost: bool = True

    def as_refusal(self):
        return FormulationResult(
            status="REFUSED",
            mode=self.problem.mode,
            refusal_reasons=self.refusal_reasons,
            warnings=self.warnings,
            excluded_ingredients=self.excluded,
            solver_status="non lancé",
        )


def prepare(problem: Problem) -> Prepared:
    out = Prepared(problem=problem)
    reasons = out.refusal_reasons

    if not problem.requirements:
        reasons.append("Aucun besoin nutritionnel validé n'est disponible pour ce profil d'animal.")
    if problem.dm_intake_min_kg is None and problem.dm_intake_max_kg is None:
        reasons.append(
            "L'ingestion de matière sèche (kg MS/jour) n'est pas renseignée "
            "dans la référence nutritionnelle : "
            "impossible de dimensionner la ration."
        )
    if not problem.ingredients:
        reasons.append("Aucun ingrédient n'a été proposé.")

    constrained = {r.nutrient_id for r in problem.requirements}
    kept = []
    for ing in problem.ingredients:
        why = []
        if not ing.dm_fraction:
            why.append("teneur en matière sèche inconnue")
        missing = [
            problem.nutrients[n].code for n in sorted(constrained) if n not in ing.composition_per_kg_dm
        ]
        if missing:
            why.append(f"valeur(s) validée(s) inconnue(s) pour : {', '.join(missing)}")
        if problem.mode == Mode.ECONOMIC and ing.price_per_kg_as_fed is None:
            why.append("prix inconnu (indispensable en mode économique)")
        if ing.max_as_fed_kg_per_day is not None and ing.max_as_fed_kg_per_day <= 0:
            why.append("quantité disponible nulle")
        if why:
            out.excluded.append({"ingredient_id": ing.id, "name": ing.name, "reasons": why})
            out.warnings.append(f"« {ing.name} » exclu : {' ; '.join(why)}.")
        else:
            kept.append(ing)
            if ing.price_is_demo:
                out.warnings.append(f"Le prix de « {ing.name} » est une donnée DEMO.")

    if problem.ingredients and not kept:
        reasons.append("Aucun ingrédient proposé ne dispose de toutes les données validées nécessaires.")

    if kept and any(i.price_per_kg_as_fed is None for i in kept):
        out.use_cost = False
        out.warnings.append("Certains prix sont inconnus : le coût n'est pas pris en compte ni calculé.")

    if problem.mode == Mode.BALANCED and not any(
        r.target_value is not None or (r.min_value is not None and r.max_value is not None)
        for r in problem.requirements
    ):
        out.warnings.append(
            "Aucune cible n'est définie dans la référence : "
            "le mode équilibré se limite au respect des contraintes "
            "(avec le coût comme critère s'il est connu)."
        )

    problem.ingredients = kept
    out.refused = bool(reasons)
    return out
