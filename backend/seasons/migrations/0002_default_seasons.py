"""Calendrier indicatif des saisons au Sénégal (ajustable selon la zone par un administrateur)."""

from django.db import migrations

SEASONS = [
    (
        "SECHE_FRAICHE",
        "Saison sèche fraîche",
        11,
        2,
        False,
        "Novembre à février : après les récoltes, fanes et résidus de culture encore disponibles.",
        10,
    ),
    (
        "SECHE_CHAUDE",
        "Saison sèche chaude (soudure)",
        3,
        6,
        True,
        "Mars à juin : forte chaleur, fourrages rares et plus chers, période de soudure.",
        20,
    ),
    (
        "HIVERNAGE",
        "Hivernage",
        7,
        10,
        False,
        "Juillet à octobre : saison des pluies, herbe verte disponible, humidité.",
        30,
    ),
]


def create(apps, schema_editor):
    Season = apps.get_model("seasons", "Season")
    for code, name, start, end, hot, description, order in SEASONS:
        Season.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "start_month": start,
                "end_month": end,
                "is_hot": hot,
                "description": description,
                "sort_order": order,
            },
        )


def remove(apps, schema_editor):
    apps.get_model("seasons", "Season").objects.filter(code__in=[s[0] for s in SEASONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("seasons", "0001_initial")]
    operations = [migrations.RunPython(create, remove)]
