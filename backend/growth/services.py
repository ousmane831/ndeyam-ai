"""Services de suivi de croissance (accès aux données)."""

from django.db.models import Q

from .calculations import WeightPoint, growth_series, mean
from .models import GrowthMonitoringRange


def weight_points(animal, include_initial=True):
    points = [WeightPoint(w.weighed_on, w.weight_kg, w.method) for w in animal.weighings.all()]
    # Le poids initial déclaré compte comme mesure s'il n'existe pas de pesée le jour de l'enregistrement.
    if include_initial and animal.initial_weight_kg and not any(p.on == animal.registered_on for p in points):
        points.append(WeightPoint(animal.registered_on, animal.initial_weight_kg, "DECLARED", "initial"))
    return points


def applicable_range(animal, on_date=None):
    """
    Plage de suivi VALIDÉE (non DEMO) la plus spécifique qui s'applique à l'animal, ou None.
    Une plage bornée en âge ne s'applique pas à un animal dont l'âge est inconnu.
    """
    age = animal.age_in_days(on_date)
    qs = GrowthMonitoringRange.objects.usable_for_engine().filter(species=animal.species)
    qs = qs.filter(Q(breed__isnull=True) | Q(breed=animal.breed_id))
    qs = qs.filter(Q(category__isnull=True) | Q(category=animal.category_id))
    qs = qs.filter(Q(physiological_stage__isnull=True) | Q(physiological_stage=animal.physiological_stage_id))
    qs = qs.filter(Q(sex="") | Q(sex=animal.sex))
    if age is None:
        qs = qs.filter(age_min_days__isnull=True, age_max_days__isnull=True)
    else:
        qs = qs.filter(Q(age_min_days__isnull=True) | Q(age_min_days__lte=age))
        qs = qs.filter(Q(age_max_days__isnull=True) | Q(age_max_days__gte=age))

    def specificity(r):
        return sum(
            x is not None and x != ""
            for x in (
                r.breed_id,
                r.category_id,
                r.physiological_stage_id,
                r.sex,
                r.age_min_days,
                r.age_max_days,
            )
        )

    candidates = sorted(qs.select_related("source"), key=lambda r: (-specificity(r), -r.pk))
    return candidates[0] if candidates else None


def compare_to_range(adg, growth_range):
    """Situe un GMD par rapport à une plage : 'below', 'within', 'above' (None si non comparable)."""
    if adg is None or growth_range is None:
        return None
    if growth_range.adg_min_g is not None and adg < growth_range.adg_min_g:
        return "below"
    if growth_range.adg_max_g is not None and adg > growth_range.adg_max_g:
        return "above"
    return "within"


def range_payload(growth_range):
    if growth_range is None:
        return None
    return {
        "id": growth_range.pk,
        "name": growth_range.name,
        "adg_min_g": str(growth_range.adg_min_g) if growth_range.adg_min_g is not None else None,
        "adg_max_g": str(growth_range.adg_max_g) if growth_range.adg_max_g is not None else None,
        "source": str(growth_range.source),
    }


def animal_growth(animal):
    from decimal import Decimal

    series = growth_series(weight_points(animal))
    growth_range = applicable_range(animal)
    latest = series["latest_interval"]
    latest_adg = Decimal(latest["adg_g_per_day"]) if latest and latest["adg_g_per_day"] else None
    series["monitoring_range"] = range_payload(growth_range)
    series["latest_vs_range"] = compare_to_range(latest_adg, growth_range)
    series["monitoring_note"] = (
        "Comparaison à une plage de suivi validée. Il ne s'agit pas d'un diagnostic vétérinaire."
        if growth_range
        else "Aucune plage de suivi validée ne s'applique à cet animal : aucune comparaison n'est effectuée."
    )
    return series


def group_growth(group):
    from animals.models import AnimalStatus

    rows = []
    for animal in group.animals.filter(status=AnimalStatus.ACTIVE).prefetch_related("weighings"):
        series = growth_series(weight_points(animal))
        last = series["points"][-1] if series["points"] else None
        rows.append(
            {
                "animal_id": animal.pk,
                "tag_number": animal.tag_number,
                "name": animal.name,
                "last_weight_kg": last["weight_kg"] if last else None,
                "last_weighed_on": last["date"] if last else None,
                "adg_g_per_day": series["overall"]["adg_g_per_day"] if series["overall"] else None,
                "measurements": len(series["points"]),
            }
        )
    with_adg = [r["adg_g_per_day"] for r in rows if r["adg_g_per_day"] is not None]
    return {
        "group_id": group.pk,
        "group_name": group.name,
        "animals": rows,
        "animals_count": len(rows),
        "animals_with_adg": len(with_adg),
        "mean_adg_g_per_day": str(mean(with_adg)) if with_adg else None,
        "note": "La moyenne ne porte que sur les animaux ayant au moins deux mesures à dates différentes.",
    }
