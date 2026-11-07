"""
Nomenclatures de base (aucune donnée zootechnique chiffrée).

- Espèces : ovins actifs ; caprins et bovins créés mais inactifs (activation future sans code).
- Races ovines couramment élevées au Sénégal, catégories, stades physiologiques, objectifs.
Toutes ces entrées sont modifiables par un administrateur.
"""

from django.db import migrations

SPECIES = [
    ("OVIN", "Ovin", "Ovis aries", True),
    ("CAPRIN", "Caprin", "Capra hircus", False),
    ("BOVIN", "Bovin", "Bos taurus / Bos indicus", False),
]

OVINE_BREEDS = [
    ("Peul-Peul", "Peulh, Fulani"),
    ("Touabire", "Touabir, Maure à poils ras"),
    ("Ladoum", ""),
    ("Djallonké", "Mouton nain d'Afrique de l'Ouest"),
    ("Waralé", "Croisement Touabire × Peul-Peul"),
]

OVINE_CATEGORIES = [
    ("AGNEAU_NON_SEVRE", "Agneau / agnelle non sevré(e)", 10),
    ("JEUNE_SEVRE", "Jeune sevré en croissance", 20),
    ("ANTENAIS", "Antenais / antenaise", 30),
    ("BREBIS", "Brebis", 40),
    ("BELIER", "Bélier", 50),
    ("MOUTON_EMBOUCHE", "Mouton à l'embouche", 60),
]

OVINE_STAGES = [
    ("CROISSANCE", "Croissance", 10),
    ("ENTRETIEN", "Entretien", 20),
    ("ENGRAISSEMENT", "Engraissement / finition", 30),
    ("LUTTE", "Préparation à la lutte", 40),
    ("GESTATION_DEBUT", "Début de gestation", 50),
    ("GESTATION_FIN", "Fin de gestation", 60),
    ("LACTATION", "Lactation", 70),
]

OBJECTIVES = [
    ("ENTRETIEN", "Entretien", 10),
    ("CROISSANCE", "Croissance", 20),
    ("EMBOUCHE", "Embouche / engraissement", 30),
    ("TABASKI", "Préparation à la Tabaski", 40),
    ("REPRODUCTION", "Reproduction", 50),
    ("LAIT", "Production laitière", 60),
]


def seed(apps, schema_editor):
    Species = apps.get_model("animals", "Species")
    Breed = apps.get_model("animals", "Breed")
    AnimalCategory = apps.get_model("animals", "AnimalCategory")
    PhysiologicalStage = apps.get_model("animals", "PhysiologicalStage")
    ProductionObjective = apps.get_model("animals", "ProductionObjective")

    for code, name, scientific, active in SPECIES:
        Species.objects.update_or_create(
            code=code, defaults={"name": name, "scientific_name": scientific, "is_active": active}
        )
    ovin = Species.objects.get(code="OVIN")
    for name, local in OVINE_BREEDS:
        Breed.objects.get_or_create(species=ovin, name=name, defaults={"local_names": local})
    for code, name, order in OVINE_CATEGORIES:
        AnimalCategory.objects.get_or_create(species=ovin, code=code, defaults={"name": name, "sort_order": order})
    for code, name, order in OVINE_STAGES:
        PhysiologicalStage.objects.get_or_create(species=ovin, code=code, defaults={"name": name, "sort_order": order})
    for code, name, order in OBJECTIVES:
        ProductionObjective.objects.get_or_create(code=code, defaults={"name": name, "sort_order": order})


class Migration(migrations.Migration):
    dependencies = [("animals", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
