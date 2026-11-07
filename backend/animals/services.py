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
