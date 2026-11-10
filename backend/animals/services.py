"""Services métier des animaux."""


def animal_history(animal):
    """Chronologie unifiée de l'animal, du plus récent au plus ancien. Aucune donnée n'est déduite."""
    events = []
    for w in animal.weighings.all():
        events.append(
            {
                "type": "weighing",
                "date": w.weighed_on,
                "label": f"Pesée : {w.weight_kg} kg",
                "details": {
                    "weight_kg": str(w.weight_kg),
                    "method": w.get_method_display(),
                    "observations": w.observations,
                },
            }
        )
    for o in animal.observation_entries.all():
        events.append(
            {
                "type": "observation",
                "date": o.observed_on,
                "label": f"Observation ({o.get_kind_display()})",
                "details": {"text": o.text},
            }
        )
    for r in animal.rations.select_related("formula"):
        events.append(
            {
                "type": "ration",
                "date": r.start_date,
                "label": f"Ration « {r.name} » ({r.get_status_display()})",
                "details": {"formula": r.formula.name, "end_date": r.end_date, "status": r.status},
            }
        )
    for f in animal.feeding_records.all():
        consumed = (
            f"{f.quantity_consumed_kg} kg consommés"
            if f.quantity_consumed_kg is not None
            else "consommation non mesurée"
        )
        events.append(
            {
                "type": "feeding",
                "date": f.fed_on,
                "label": f"Distribution : {f.quantity_distributed_kg} kg ({consumed})",
                "details": {
                    "quantity_calculated_kg": f.quantity_calculated_kg and str(f.quantity_calculated_kg),
                    "quantity_distributed_kg": str(f.quantity_distributed_kg),
                    "quantity_consumed_kg": f.quantity_consumed_kg and str(f.quantity_consumed_kg),
                },
            }
        )
    events.append(
        {
            "type": "registration",
            "date": animal.registered_on,
            "label": "Enregistrement de l'animal",
            "details": {},
        }
    )
    events.sort(key=lambda e: e["date"], reverse=True)
    return events


def group_profile(group):
    """
    Profil moyen d'un lot pour la formulation, déduit de ses animaux présents :
    espèce, race, catégorie et stade les plus fréquents, poids moyen des dernières pesées, âge moyen.
    Seules des données enregistrées sont utilisées ; ce qui manque reste vide et est signalé.
    """
    from collections import Counter
    from decimal import Decimal

    from .models import AnimalStatus

    animals = list(
        group.animals.filter(status=AnimalStatus.ACTIVE).select_related(
            "species", "breed", "category", "physiological_stage"
        )
    )
    profile = {"head_count": len(animals), "notes": []}
    if not animals:
        profile["notes"].append(f"Le lot « {group.name} » ne compte aucun animal présent.")
        return profile

    def majority(field, label):
        values = Counter(getattr(a, field) for a in animals if getattr(a, field) is not None)
        if not values:
            return None
        value, count = values.most_common(1)[0]
        if count < len(animals):
            profile["notes"].append(
                f"Lot mixte, {label} : valeur la plus fréquente retenue "
                f"({value}, {count} animaux sur {len(animals)})."
            )
        return value

    profile["species"] = majority("species", "espèce") or group.species
    profile["breed"] = majority("breed", "race")
    profile["category"] = majority("category", "catégorie")
    profile["physiological_stage"] = majority("physiological_stage", "stade")

    weights = []
    for a in animals:
        last = a.weighings.order_by("-weighed_on").first()
        weight = last.weight_kg if last else a.initial_weight_kg
        if weight is not None:
            weights.append(Decimal(weight))
    if weights:
        profile["weight_kg"] = (sum(weights) / len(weights)).quantize(Decimal("0.01"))
        profile["notes"].append(
            f"Poids moyen du lot : {str(profile['weight_kg']).replace('.', ',')} kg "
            f"({len(weights)} animal(aux) pesé(s) sur {len(animals)})."
        )
    ages = [Decimal(a.age_in_days()) / Decimal("30.44") for a in animals if a.birth_date]
    if ages:
        profile["age_months"] = (sum(ages) / len(ages)).quantize(Decimal("0.1"))
    return profile
