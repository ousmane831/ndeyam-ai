"""
Réponses de l'assistant vocal, calculées sur les données de l'exploitation (jamais par un modèle de langage).

Chaque réponse existe en deux versions : le texte parlé (wolof ou pulaar, nombres en lettres, quantités
arrondies à une valeur simple à dire, UNE PHRASE COURTE PAR INFORMATION, chacune lue séparément) et le texte
affiché en français (chiffres exacts). Les rations proposées sont celles en cours dans l'exploitation :
elles ont déjà passé la règle « une estimation ne nourrit jamais un animal ».
"""

import re
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .intents import phrases
from .numbers import spell, spoken_amount, spoken_quantity

COST_DAYS = 30


def _fr_kg(kg):
    kg = Decimal(kg)
    if kg < 1:
        return f"{int(round(kg * 1000 / 10) * 10)} g"
    return f"{str(kg.quantize(Decimal('0.1'))).replace('.', ',')} kg"


def _fr_money(value):
    return f"{int(Decimal(value).quantize(Decimal('1'))):,} FCFA".replace(",", " ")


def _plain(name):
    return name.replace("[DEMO] ", "").replace("[DEMO]", "").strip()


def _spoken_name(name, language):
    """Nom lisible par la synthèse : sans préfixe DEMO, nombres écrits en lettres (« Agneaux 2026 »)."""
    return re.sub(r"\d+", lambda m: spell(int(m.group()), language), _plain(name))


def _head_count(ration):
    if ration.group_id:
        from animals.models import AnimalStatus

        return ration.group.animals.filter(status=AnimalStatus.ACTIVE).count() or 1
    return 1


def _ration(farm, language, tpl, units):
    from feeding.models import Ration, RationStatus

    ration = (
        Ration.objects.filter(farm=farm, status=RationStatus.ACTIVE)
        .select_related("formula", "group", "animal")
        .order_by("-start_date")
        .first()
    )
    if ration is None:
        return [tpl["ration_none"]], "Aucune ration en cours dans l'exploitation.", {}
    heads = _head_count(ration)
    target = ration.group.name if ration.group_id else (ration.animal.name or ration.animal.tag_number)
    items = [i for i in ration.formula.items.select_related("ingredient") if i.quantity_as_fed_kg]
    sentences = [tpl["ration"].format(group=_spoken_name(target, language))]
    sentences += [
        tpl["ration_item"].format(
            food=_spoken_name(i.ingredient.name, language),
            quantity=spoken_quantity(i.quantity_as_fed_kg * heads, language, units),
        )
        for i in items
    ]
    shown = ", ".join(f"{_fr_kg(i.quantity_as_fed_kg * heads)} de {_plain(i.ingredient.name)}" for i in items)
    cost = (ration.formula.cost_per_day or 0) * heads
    fr = f"Ration « {ration.name} » pour {target} ({heads} animal(aux)), chaque jour : {shown}."
    if cost:
        fr += f" Coût : {_fr_money(cost)} par jour."
    data = {
        "ration": ration.name,
        "target": target,
        "head_count": heads,
        "items": [
            {"food": _plain(i.ingredient.name), "kg_per_day": str(i.quantity_as_fed_kg * heads)}
            for i in items
        ],
    }
    return sentences, fr, data


def _weighing(farm, language, tpl, units):
    from alerts.models import Alert, AlertStatus, AlertType
    from animals.models import AnimalGroup
    from animals.services import group_profile

    due = Alert.objects.filter(
        farm=farm,
        alert_type=AlertType.WEIGHING_REMINDER,
        status__in=[AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED],
    ).count()
    sentences = [tpl["weighing"].format(count=spell(due, language)) if due else tpl["weighing_none"]]
    fr = f"{due} animal(aux) à peser." if due else "Aucun animal à peser pour le moment."
    data = {"to_weigh": due}
    group = AnimalGroup.objects.filter(farm=farm, is_active=True).order_by("name").first()
    if group is not None:
        weight = group_profile(group).get("weight_kg")
        if weight:
            sentences += [
                tpl["group"].format(group=_spoken_name(group.name, language)),
                tpl["weighing_average"].format(weight=spoken_quantity(weight, language, units)),
            ]
            fr += f" Poids moyen du lot « {group.name} » : {_fr_kg(weight)}."
            data["group_average_kg"] = str(weight)
    return sentences, fr, data


def _cost(farm, language, tpl, units):
    from feeding.models import FeedingRecord

    since = timezone.localdate() - timedelta(days=COST_DAYS)
    total = FeedingRecord.objects.filter(farm=farm, fed_on__gte=since).aggregate(s=Sum("estimated_cost"))["s"]
    if not total:
        return [tpl["cost_none"]], f"Aucun coût d'alimentation enregistré sur {COST_DAYS} jours.", {}
    return (
        [tpl["cost"], tpl["cost_amount"].format(amount=spoken_amount(total, language, units))],
        f"Coût de l'alimentation sur les {COST_DAYS} derniers jours : {_fr_money(total)}.",
        {"days": COST_DAYS, "cost": str(total)},
    )


def _growth(farm, language, tpl, units):
    from animals.models import AnimalGroup
    from growth.services import group_growth

    for group in AnimalGroup.objects.filter(farm=farm, is_active=True).order_by("name"):
        adg = group_growth(group).get("mean_adg_g_per_day")
        if adg:
            grams = int(Decimal(adg).quantize(Decimal("1")))
            return (
                [
                    tpl["group"].format(group=_spoken_name(group.name, language)),
                    tpl["growth"].format(adg=f"{spell(grams, language)} {units['gram']}"),
                ],
                f"Lot « {group.name} » : gain moyen quotidien de {grams} g/j.",
                {"group": group.name, "adg_g_per_day": str(adg)},
            )
    return [tpl["growth_none"]], "Pas assez de pesées pour calculer la croissance.", {}


def _tasks(farm, language, tpl, units):
    from alerts.models import Alert, AlertStatus

    count = Alert.objects.filter(farm=farm, status__in=[AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]).count()
    if not count:
        return [tpl["tasks_none"]], "Rien d'urgent aujourd'hui.", {"open_alerts": 0}
    return (
        [tpl["tasks"].format(count=spell(count, language))],
        f"{count} chose(s) à faire aujourd'hui.",
        {"open_alerts": count},
    )


BUILDERS = {"ration": _ration, "weighing": _weighing, "cost": _cost, "growth": _growth, "tasks": _tasks}
LABELS = {
    "ration": "Ration du jour",
    "weighing": "Pesées",
    "cost": "Coût de l'alimentation",
    "growth": "Croissance",
    "tasks": "À faire aujourd'hui",
    "unknown": "Demande non comprise",
}


def build_answer(intent, farm, language):
    """(phrases parlées, texte affiché en français, données) pour une intention et une exploitation."""
    table = phrases()[language]
    tpl, units = table["templates"], table["units"]
    if intent not in BUILDERS:
        return (
            [tpl["unknown"]],
            "Demande non comprise : ration, pesées, coût, croissance ou tâches du jour.",
            {},
        )
    sentences, fr, data = BUILDERS[intent](farm, language, tpl, units)
    if farm.is_demo:
        sentences = [*sentences, tpl["demo"]]
        fr = f"{fr} (Données de démonstration fictives.)"
    return sentences, fr, data
