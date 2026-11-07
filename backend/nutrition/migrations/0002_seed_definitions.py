"""
Définitions de structure du référentiel nutritionnel.

Cette migration crée UNIQUEMENT des définitions (catégories d'ingrédients, nutriments avec leur
unité et leur système). Elle ne contient AUCUNE valeur de composition ni AUCUN besoin animal :
ces valeurs doivent être importées depuis des sources identifiées puis validées.

Les systèmes INRA et NRC sont créés avec leurs principales unités énergétiques et protéiques.
Un expert doit vérifier ces définitions et peut les compléter dans l'administration.
"""

from django.db import migrations

INGREDIENT_CATEGORIES = [
    ("CEREALES", "Céréales", 10),
    ("SOUS_PRODUITS_CEREALIERS", "Sous-produits céréaliers", 20),
    ("TOURTEAUX", "Tourteaux", 30),
    ("FOURRAGES", "Fourrages", 40),
    ("RESIDUS_CULTURE", "Fanes et résidus de culture", 50),
    ("SOURCES_MINERALES", "Sources minérales", 60),
    ("COMPLEMENTS", "Compléments alimentaires", 70),
    ("AUTRES", "Autres ingrédients locaux", 80),
]

# code, nom, catégorie, unité de quantité, base, ordre
UNIVERSAL_NUTRIENTS = [
    ("MS", "Matière sèche", "DRY_MATTER", "g", "AS_FED", 10),
    ("MAT", "Matières azotées totales (protéines brutes)", "PROTEIN", "g", "DM", 30),
    ("MG", "Matières grasses", "FAT", "g", "DM", 40),
    ("MM", "Matières minérales", "MINERAL", "g", "DM", 50),
    ("CB", "Cellulose brute", "FIBER", "g", "DM", 60),
    ("NDF", "Fibres au détergent neutre (NDF)", "FIBER", "g", "DM", 61),
    ("ADF", "Fibres au détergent acide (ADF)", "FIBER", "g", "DM", 62),
    ("CA", "Calcium", "MINERAL", "g", "DM", 70),
    ("P", "Phosphore", "MINERAL", "g", "DM", 71),
]

SYSTEMS = {
    "INRA": {
        "name": "INRA",
        "version": "2018",
        "description": "Système INRA (Alimentation des ruminants). Définitions à vérifier par un expert.",
        "nutrients": [
            ("UFL", "Unité fourragère lait", "ENERGY", "UFL", "DM", 20),
            ("UFV", "Unité fourragère viande", "ENERGY", "UFV", "DM", 21),
            ("PDI", "Protéines digestibles dans l'intestin", "PROTEIN", "g", "DM", 31),
        ],
    },
    "NRC": {
        "name": "NRC",
        "version": "2007 (petits ruminants)",
        "description": "Système NRC (Nutrient Requirements of Small Ruminants). Définitions à vérifier par un expert.",
        "nutrients": [
            ("EM", "Énergie métabolisable", "ENERGY", "Mcal", "DM", 20),
            ("PM", "Protéines métabolisables", "PROTEIN", "g", "DM", 31),
        ],
    },
}


def seed(apps, schema_editor):
    IngredientCategory = apps.get_model("nutrition", "IngredientCategory")
    Nutrient = apps.get_model("nutrition", "Nutrient")
    NutritionSystem = apps.get_model("nutrition", "NutritionSystem")

    for code, name, order in INGREDIENT_CATEGORIES:
        IngredientCategory.objects.get_or_create(code=code, defaults={"name": name, "sort_order": order})

    for code, name, category, unit, basis, order in UNIVERSAL_NUTRIENTS:
        Nutrient.objects.get_or_create(
            code=code,
            system=None,
            defaults={"name": name, "category": category, "amount_unit": unit, "basis": basis, "sort_order": order},
        )

    for code, spec in SYSTEMS.items():
        system, _ = NutritionSystem.objects.get_or_create(
            code=code,
            defaults={"name": spec["name"], "version": spec["version"], "description": spec["description"]},
        )
        for n_code, name, category, unit, basis, order in spec["nutrients"]:
            Nutrient.objects.get_or_create(
                code=n_code,
                system=system,
                defaults={"name": name, "category": category, "amount_unit": unit, "basis": basis, "sort_order": order},
            )


class Migration(migrations.Migration):
    dependencies = [("nutrition", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
