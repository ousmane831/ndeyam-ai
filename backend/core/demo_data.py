"""
Jeu de données de DÉMONSTRATION de NDEYAM AI (commande `load_demo_data`).

Règles appliquées :
- tout est marqué DEMO (comptes identifiables, exploitations et référentiel `is_demo`,
  préfixe « [DEMO] ») ;
- les valeurs nutritionnelles sont FICTIVES, choisies pour illustrer l'interface :
  elles ne proviennent d'aucune
  table publiée et ne sont jamais validées (la base l'interdit pour une donnée DEMO) ;
- le moteur ne les utilise que pour les exploitations DEMO ; une exploitation réelle les exclut ;
- aucun mot de passe n'est écrit ici : il est fourni à la commande ou généré aléatoirement.

Le chargement est réversible (`--reset`) et ne touche à aucune donnée réelle.
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

DEMO_DOMAIN = "demo.ndeyam.example"  # domaine réservé (RFC 2606) : aucune adresse réelle
PREFIX = "[DEMO]"

ACCOUNTS = [
    {
        "key": "eleveur",
        "email": f"eleveur@{DEMO_DOMAIN}",
        "first_name": "Fatou",
        "last_name": "Diop (DEMO)",
        "role": "ELEVEUR",
    },
    {
        "key": "eleveur2",
        "email": f"eleveur2@{DEMO_DOMAIN}",
        "first_name": "Ibrahima",
        "last_name": "Ndiaye (DEMO)",
        "role": "ELEVEUR",
    },
    {
        "key": "expert",
        "email": f"expert@{DEMO_DOMAIN}",
        "first_name": "Aminata",
        "last_name": "Sow (DEMO)",
        "role": "EXPERT",
    },
]

# Teneurs FICTIVES. MS en g/kg de produit brut ; MAT, CB, CA, P en g/kg de MS ; UFL par kg de MS.
INGREDIENTS = [
    (
        "Fane d'arachide",
        "FOURRAGES",
        {"MS": 900, "MAT": 110, "UFL": "0.60", "CB": 300, "CA": 12, "P": 2},
        150,
    ),
    (
        "Paille de mil",
        "RESIDUS_CULTURE",
        {"MS": 920, "MAT": 40, "UFL": "0.45", "CB": 400, "CA": 3, "P": 1},
        60,
    ),
    (
        "Son de mil",
        "SOUS_PRODUITS_CEREALIERS",
        {"MS": 900, "MAT": 110, "UFL": "0.85", "CB": 90, "CA": 1, "P": 9},
        125,
    ),
    (
        "Tourteau d'arachide",
        "TOURTEAUX",
        {"MS": 920, "MAT": 480, "UFL": "1.05", "CB": 70, "CA": 2, "P": 6},
        300,
    ),
    ("Graine de coton", "TOURTEAUX", {"MS": 920, "MAT": 230, "UFL": "0.95", "CB": 230, "CA": 2, "P": 7}, 200),
    ("Mélasse de canne", "COMPLEMENTS", {"MS": 750, "MAT": 40, "UFL": "0.85", "CB": 0, "CA": 8, "P": 1}, 175),
    (
        "Coquilles d'huîtres broyées",
        "SOURCES_MINERALES",
        {"MS": 990, "MAT": 0, "UFL": "0", "CB": 0, "CA": 350, "P": 0},
        100,
    ),
]

# Besoins FICTIFS (quantités par animal et par jour, sauf CB : teneur maximale de la ration).
REFERENCES = [
    {
        "name": "Mouton d'embouche 25–45 kg (valeurs fictives)",
        "category": "MOUTON_EMBOUCHE",
        "stage": "ENGRAISSEMENT",
        "objective": "TABASKI",
        "weight": (25, 45),
        "dmi": ("1.10", "1.50"),
        "requirements": [
            ("UFL", "DAILY_AMOUNT", "0.95", "1.05", None),
            ("MAT", "DAILY_AMOUNT", "130", "150", "220"),
            ("CA", "DAILY_AMOUNT", "5", None, None),
            ("P", "DAILY_AMOUNT", "3", None, None),
            ("CB", "DIET_CONCENTRATION", None, None, "260"),
        ],
    },
    {
        "name": "Brebis à l'entretien 35–50 kg (valeurs fictives)",
        "category": "BREBIS",
        "stage": "ENTRETIEN",
        "objective": "ENTRETIEN",
        "weight": (35, 50),
        "dmi": ("1.00", "1.40"),
        "requirements": [
            ("UFL", "DAILY_AMOUNT", "0.70", None, None),
            ("MAT", "DAILY_AMOUNT", "80", None, "180"),
            ("CA", "DAILY_AMOUNT", "4", None, None),
            ("P", "DAILY_AMOUNT", "2.5", None, None),
        ],
    },
]

# Contraintes d'incorporation FICTIVES (% de la MS de la ration).
CONSTRAINTS = [
    ("ingredient", "Tourteau d'arachide", None, "25"),
    ("ingredient", "Mélasse de canne", None, "10"),
    ("ingredient", "Coquilles d'huîtres broyées", None, "2"),
    ("category", "FOURRAGES", "25", None),
]

FARMS = [
    {
        "key": "thies",
        "owner": "eleveur",
        "name": "Bergerie de Thiès",
        "region": "Thiès",
        "locality": "Pout",
        "description": "Exploitation fictive de démonstration : embouche pour la Tabaski "
        "et troupeau de brebis.",
    },
    {
        "key": "kaolack",
        "owner": "eleveur2",
        "name": "Élevage de Kaolack",
        "region": "Kaolack",
        "locality": "Ndoffane",
        "description": "Seconde exploitation fictive, appartenant à un autre éleveur "
        "(illustre l'isolation des données).",
    },
]

DOCUMENT_PAGES = [
    [
        "[DEMO] Fiche pratique fictive - Stockage des aliments du betail",
        "Document de demonstration : contenu illustratif, non valide scientifiquement.",
        "",
        "1. Conserver le tourteau d'arachide dans un local sec et aere.",
        "Une humidite elevee favorise les moisissures et le developpement d'aflatoxines.",
        "2. Stocker les sacs sur des palettes, a distance des murs.",
        "3. Utiliser les lots les plus anciens en premier.",
    ],
    [
        "[DEMO] Suite - Fourrages et residus de culture",
        "La fane d'arachide se conserve en bottes, a l'abri de la pluie et du soleil direct.",
        "La paille de mil est un aliment de lest : sa valeur nutritive est faible.",
        "Pour toute question de sante animale, consulter un veterinaire.",
    ],
]


@dataclass
class Summary:
    accounts: int = 0
    farms: int = 0
    animals: int = 0
    weighings: int = 0
    ingredients: int = 0
    compositions: int = 0
    formulas: int = 0
    feeding_records: int = 0
    alerts: int = 0
    documents: int = 0


def demo_users():
    from accounts.models import User

    return User.objects.filter(email__endswith=f"@{DEMO_DOMAIN}")


def is_loaded():
    from farms.models import Farm

    return demo_users().exists() or Farm.objects.filter(is_demo=True, name__startswith=PREFIX).exists()


# --- Suppression (uniquement les données DEMO) ---------------------------------------------------


@transaction.atomic
def remove_demo_data():
    """Supprime le jeu DEMO. Chaque filtre exige `is_demo=True` ou un compte du domaine DEMO."""
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

    from alerts.models import Alert
    from assistant.models import AIConversation
    from farms.models import Farm
    from feeding.models import FeedingRecord, Ration
    from formulations.models import FeedFormula
    from governance.models import ActivityLog, ImportBatch, SourceDocument, ValidationRecord
    from knowledge_base.models import TechnicalDocument
    from nutrition.models import InclusionConstraint, Ingredient, IngredientComposition, NutritionalReference

    users = demo_users()
    farms = Farm.objects.filter(is_demo=True, name__startswith=PREFIX)
    counts = {"exploitations": farms.count(), "comptes": users.count()}
    FeedingRecord.objects.filter(farm__in=farms).delete()
    Ration.objects.filter(farm__in=farms).delete()
    FeedFormula.objects.filter(farm__in=farms).delete()
    ActivityLog.objects.filter(farm__in=farms).delete()
    farms.delete()  # lots, animaux, pesées, prix, alertes d'exploitation : en cascade
    for doc in TechnicalDocument.objects.filter(is_demo=True, created_by__in=users):
        doc.file.delete(save=False)
        doc.delete()
    InclusionConstraint.objects.filter(is_demo=True, created_by__in=users).delete()
    NutritionalReference.objects.filter(is_demo=True, created_by__in=users).delete()
    IngredientComposition.objects.filter(is_demo=True, created_by__in=users).delete()
    Ingredient.objects.filter(is_demo=True, created_by__in=users).delete()
    SourceDocument.objects.filter(is_demo=True, created_by__in=users).delete()
    Alert.objects.filter(recipient__in=users).delete()
    AIConversation.objects.filter(user__in=users).delete()
    ValidationRecord.objects.filter(actor__in=users).delete()
    ImportBatch.objects.filter(imported_by__in=users).delete()
    ActivityLog.objects.filter(actor__in=users).delete()
    OutstandingToken.objects.filter(user__in=users).delete()
    users.delete()
    return counts


# --- Chargement ----------------------------------------------------------------------------------


def _d(value):
    return None if value is None else Decimal(str(value))


def _make_pdf(pages):
    """PDF texte minimal (Helvetica), lisible par l'extraction de la base documentaire."""

    def esc(line):
        return line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", None]
    kids, font_id = [], 3 + 2 * len(pages)
    for i, lines in enumerate(pages):
        page_id, content_id = 3 + 2 * i, 4 + 2 * i
        kids.append(f"{page_id} 0 R")
        stream = (
            "BT /F1 12 Tf 50 780 Td 18 TL " + " ".join(f"({esc(ln)}) '" for ln in lines) + " ET"
        ).encode("latin-1")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {content_id} 0 R "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode()
        )
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>".encode()
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for n, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def _weight_series(start_kg, adg_g, start_date, every_days, count, method="SCALE"):
    """Pesées déterministes (pas d'aléatoire) : croissance régulière avec de petites variations fixes."""
    wobble = [0, 0.4, -0.3, 0.2, -0.2, 0.3, -0.1]
    for i in range(count):
        day = start_date + timedelta(days=i * every_days)
        weight = start_kg + adg_g * i * every_days / 1000 + wobble[i % len(wobble)]
        yield day, Decimal(str(round(weight, 1))), method


@transaction.atomic
def load_demo_data(password, today=None):
    from accounts.models import User
    from alerts.engine import evaluate_farm, evaluate_reviewers
    from alerts.models import Alert
    from animals.models import (
        Animal,
        AnimalCategory,
        AnimalGroup,
        AnimalObservation,
        AnimalStatus,
        Breed,
        PhysiologicalStage,
        ProductionObjective,
        Species,
    )
    from farms.models import Farm, FarmMembership
    from feeding.models import FeedingRecord, Ration
    from feeding.serializers import FeedingRecordSerializer
    from formulations.engine_service import run_formulation
    from formulations.models import FormulaStatus
    from governance.models import SourceDocument
    from growth.models import Weighing
    from knowledge_base.ingestion import process_document, sha256_of
    from knowledge_base.models import TechnicalDocument
    from nutrition.models import (
        InclusionConstraint,
        Ingredient,
        IngredientCategory,
        IngredientComposition,
        IngredientPrice,
        Nutrient,
        NutritionalReference,
        NutritionalRequirement,
        NutritionSystem,
    )

    today = today or timezone.localdate()
    summary = Summary()
    ovin = Species.objects.get(code="OVIN")
    cat = {c.code: c for c in AnimalCategory.objects.filter(species=ovin)}
    stage = {s.code: s for s in PhysiologicalStage.objects.all()}
    objective = {o.code: o for o in ProductionObjective.objects.all()}
    breed = {b.name: b for b in Breed.objects.filter(species=ovin)}
    nutrient = {n.code: n for n in Nutrient.objects.all()}
    icat = {c.code: c for c in IngredientCategory.objects.all()}
    inra = NutritionSystem.objects.get(code="INRA")

    # Comptes
    users = {}
    for spec in ACCOUNTS:
        users[spec["key"]] = User.objects.create_user(
            email=spec["email"],
            password=password,
            role=spec["role"],
            first_name=spec["first_name"],
            last_name=spec["last_name"],
        )
    summary.accounts = len(users)
    expert = users["expert"]

    # Exploitations
    farms = {}
    for spec in FARMS:
        farm = Farm.objects.create(
            name=f"{PREFIX} {spec['name']}",
            region=spec["region"],
            locality=spec["locality"],
            description=spec["description"],
            is_demo=True,
            created_by=users[spec["owner"]],
        )
        FarmMembership.objects.create(farm=farm, user=users[spec["owner"]], role="OWNER")
        farms[spec["key"]] = farm
    FarmMembership.objects.create(farm=farms["thies"], user=expert, role="EXPERT")
    summary.farms = len(farms)

    # Référentiel DEMO (jamais validé)
    source = SourceDocument.objects.create(
        title=f"{PREFIX} Table de composition fictive pour la démonstration",
        source_type="EXPERT_OPINION",
        year=today.year,
        notes="Valeurs inventées pour illustrer l'application. "
        "Ne pas utiliser pour formuler une ration réelle.",
        is_demo=True,
        created_by=expert,
    )
    ingredients = {}
    for name, category, values, _price in INGREDIENTS:
        ing = Ingredient.objects.create(
            name=f"{PREFIX} {name}",
            category=icat[category],
            source=source,
            is_demo=True,
            created_by=expert,
            description="Ingrédient de démonstration (valeurs fictives).",
        )
        ingredients[name] = ing
        for code, value in values.items():
            IngredientComposition.objects.create(
                ingredient=ing,
                nutrient=nutrient[code],
                value=_d(value),
                source=source,
                is_demo=True,
                created_by=expert,
                notes="Valeur fictive (DEMO).",
            )
            summary.compositions += 1
    summary.ingredients = len(ingredients)

    references = []
    for spec in REFERENCES:
        ref = NutritionalReference.objects.create(
            name=f"{PREFIX} {spec['name']}",
            species=ovin,
            system=inra,
            category=cat[spec["category"]],
            physiological_stage=stage[spec["stage"]],
            objective=objective[spec["objective"]],
            weight_min_kg=spec["weight"][0],
            weight_max_kg=spec["weight"][1],
            dm_intake_min_kg_day=_d(spec["dmi"][0]),
            dm_intake_max_kg_day=_d(spec["dmi"][1]),
            source=source,
            is_demo=True,
            created_by=expert,
            notes="Besoins fictifs de démonstration : ne constituent pas une recommandation.",
        )
        for code, expression, mn, target, mx in spec["requirements"]:
            NutritionalRequirement.objects.create(
                reference=ref,
                nutrient=nutrient[code],
                expression=expression,
                min_value=_d(mn),
                target_value=_d(target),
                max_value=_d(mx),
            )
        references.append(ref)
    for kind, target, mn, mx in CONSTRAINTS:
        InclusionConstraint.objects.create(
            species=ovin,
            ingredient=ingredients[target] if kind == "ingredient" else None,
            ingredient_category=icat[target] if kind == "category" else None,
            min_pct_dm=_d(mn),
            max_pct_dm=_d(mx),
            rationale="Contrainte fictive de démonstration.",
            source=source,
            is_demo=True,
            created_by=expert,
        )
    # Une composition soumise : illustre la file de validation de l'expert (elle restera non validable).
    pending = IngredientComposition.objects.filter(
        ingredient=ingredients["Graine de coton"], nutrient=nutrient["CB"]
    ).get()
    pending.status = "PENDING"
    pending.save(update_fields=["status"])

    # Prix (exploitations DEMO → prix DEMO)
    for farm in farms.values():
        for name, _cat, _values, price in INGREDIENTS:
            IngredientPrice.objects.create(
                farm=farm,
                ingredient=ingredients[name],
                price_per_kg_as_fed=price,
                valid_from=today - timedelta(days=60),
                supplier="Fournisseur fictif",
                is_demo=True,
                created_by=users["eleveur"],
            )

    # Animaux et pesées
    def animal(farm, tag, sex, **kw):
        a = Animal.objects.create(
            farm=farm,
            species=ovin,
            tag_number=tag,
            sex=sex,
            is_demo=True,
            created_by=farm.memberships.get(role="OWNER").user,
            **kw,
        )
        summary.animals += 1
        return a

    def weigh(a, series):
        for day, weight, method in series:
            Weighing.objects.create(
                animal=a,
                weighed_on=day,
                weight_kg=weight,
                method=method,
                is_demo=True,
                recorded_by=a.created_by,
            )
            summary.weighings += 1

    thies, kaolack = farms["thies"], farms["kaolack"]
    embouche = AnimalGroup.objects.create(
        farm=thies,
        name="Embouche Tabaski",
        species=ovin,
        is_demo=True,
        description="Béliers en finition pour la Tabaski (DEMO).",
    )
    brebis = AnimalGroup.objects.create(farm=thies, name="Brebis reproductrices", species=ovin, is_demo=True)
    agneaux = AnimalGroup.objects.create(farm=thies, name="Agneaux 2026", species=ovin, is_demo=True)
    start = today - timedelta(days=90)
    fattening = [
        ("TH-101", "Ladoum", "Gaïndé", 29.0, 165),
        ("TH-102", "Ladoum", "Bakhaw", 31.5, 150),
        ("TH-103", "Touabire", "Mbellé", 28.0, 140),
        ("TH-104", "Touabire", "", 30.5, 120),
        ("TH-105", "Peul-Peul", "", 27.0, 95),
        ("TH-106", "Ladoum", "Sérigne", 33.0, 180),
    ]
    fattening_animals = []
    for i, (tag, br, name, w0, adg) in enumerate(fattening):
        a = animal(
            thies,
            tag,
            "M",
            name=name,
            breed=breed.get(br),
            group=embouche,
            category=cat["MOUTON_EMBOUCHE"],
            physiological_stage=stage["ENGRAISSEMENT"],
            birth_date=today - timedelta(days=330 + 15 * i),
            registered_on=start,
            initial_weight_kg=_d(w0 - 1),
        )
        weigh(a, _weight_series(w0, adg, start, 15, 7, "SCALE" if i != 4 else "TAPE"))
        fattening_animals.append(a)
    ewes = [
        ("TH-201", "Peul-Peul", "Diarra", 41.0),
        ("TH-202", "Touabire", "Coumba", 44.0),
        ("TH-203", "Touabire", "", 39.5),
        ("TH-204", "Peul-Peul", "Penda", 42.0),
    ]
    for i, (tag, br, name, w0) in enumerate(ewes):
        a = animal(
            thies,
            tag,
            "F",
            name=name,
            breed=breed.get(br),
            group=brebis,
            category=cat["BREBIS"],
            physiological_stage=stage["ENTRETIEN"],
            birth_date=today - timedelta(days=900 + 120 * i),
            registered_on=start,
        )
        weigh(a, _weight_series(w0, 10, start, 30, 4, "VISUAL" if i == 2 else "SCALE"))
    # Brebis sans date de naissance ni stade : déclenche l'alerte « informations manquantes ».
    ewe = animal(
        thies,
        "TH-205",
        "F",
        breed=breed.get("Touabire"),
        group=brebis,
        category=cat["BREBIS"],
        registered_on=start,
    )
    weigh(ewe, _weight_series(40.0, 0, start, 45, 2))
    for i, (tag, w0, adg) in enumerate([("TH-301", 9.5, 190), ("TH-302", 8.0, 170)]):
        a = animal(
            thies,
            tag,
            "M" if i == 0 else "F",
            group=agneaux,
            category=cat["AGNEAU_NON_SEVRE"],
            physiological_stage=stage["CROISSANCE"],
            birth_date=today - timedelta(days=75),
            registered_on=today - timedelta(days=60),
        )
        weigh(a, _weight_series(w0, adg, today - timedelta(days=60), 20, 3))
    # Agneau jamais pesé, enregistré il y a 40 jours : déclenche le rappel de pesée.
    animal(
        thies,
        "TH-303",
        "F",
        group=agneaux,
        category=cat["AGNEAU_NON_SEVRE"],
        physiological_stage=stage["CROISSANCE"],
        birth_date=today - timedelta(days=70),
        registered_on=today - timedelta(days=40),
    )
    belier = animal(
        thies,
        "TH-001",
        "M",
        name="Ndiambour",
        breed=breed.get("Ladoum"),
        category=cat["BELIER"],
        physiological_stage=stage["LUTTE"],
        birth_date=today - timedelta(days=1100),
        registered_on=start,
    )
    weigh(belier, _weight_series(78.0, 20, start, 45, 3))
    sold = animal(
        thies,
        "TH-107",
        "M",
        breed=breed.get("Touabire"),
        category=cat["MOUTON_EMBOUCHE"],
        birth_date=today - timedelta(days=400),
        registered_on=start,
    )
    weigh(sold, _weight_series(36.0, 130, start, 30, 2))
    sold.status, sold.archived_at = AnimalStatus.SOLD, timezone.now()
    sold.save(update_fields=["status", "archived_at", "updated_at"])
    AnimalObservation.objects.create(
        animal=sold,
        observed_on=today - timedelta(days=10),
        kind="OTHER",
        text="Sortie : vendu au marché de Pout (DEMO).",
        author=sold.created_by,
    )
    for a, kind, text in (
        (fattening_animals[0], "FEEDING", "Mange bien la ration, aucun refus."),
        (fattening_animals[4], "GENERAL", "Croissance plus lente que le reste du lot : à surveiller."),
        (belier, "BEHAVIOR", "Calme, bonne condition générale."),
    ):
        AnimalObservation.objects.create(
            animal=a, observed_on=today - timedelta(days=5), kind=kind, text=text, author=a.created_by
        )

    for i, (tag, br, sex, w0) in enumerate(
        [
            ("KL-01", "Djallonké", "F", 24.0),
            ("KL-02", "Djallonké", "M", 26.5),
            ("KL-03", "Waralé", "F", 35.0),
            ("KL-04", "Waralé", "M", 38.0),
        ]
    ):
        a = animal(
            kaolack,
            tag,
            sex,
            breed=breed.get(br),
            category=cat["BREBIS" if sex == "F" else "BELIER"],
            birth_date=today - timedelta(days=600 + 60 * i),
            registered_on=start,
        )
        weigh(a, _weight_series(w0, 40, start, 45, 3))

    # Formules : calculées par le moteur (exploitation DEMO → données DEMO uniquement)
    embouche_ref, ewe_ref = references
    all_entries = [{"ingredient": ing} for ing in ingredients.values()]
    owner = users["eleveur"]
    profile = {
        "category": cat["MOUTON_EMBOUCHE"],
        "physiological_stage": stage["ENGRAISSEMENT"],
        "objective": objective["TABASKI"],
        "weight_kg": Decimal("35"),
    }
    economic, result = run_formulation(
        farm=thies,
        user=owner,
        name="Embouche Tabaski — économique",
        species=ovin,
        mode="ECONOMIC",
        entries=all_entries,
        reference=embouche_ref,
        profile=profile,
        group=embouche,
    )
    if result["status"] != "ESTIMATED":
        raise RuntimeError(
            f"Jeu DEMO incohérent : la formule économique n'est pas calculable ({result['status']})."
        )
    run_formulation(
        farm=thies,
        user=owner,
        name="Embouche Tabaski — équilibrée",
        species=ovin,
        mode="BALANCED",
        entries=all_entries,
        reference=embouche_ref,
        profile=profile,
        group=embouche,
    )
    run_formulation(
        farm=thies,
        user=owner,
        name="Brebis — entretien",
        species=ovin,
        mode="ECONOMIC",
        entries=all_entries,
        reference=ewe_ref,
        group=brebis,
        profile={
            "category": cat["BREBIS"],
            "physiological_stage": stage["ENTRETIEN"],
            "weight_kg": Decimal("42"),
        },
    )
    # Exemple volontairement impossible : paille seule pour un mouton d'embouche (diagnostic affiché).
    run_formulation(
        farm=thies,
        user=owner,
        name="Essai : paille de mil seule (impossible)",
        species=ovin,
        mode="ECONOMIC",
        entries=[{"ingredient": ingredients["Paille de mil"]}],
        reference=embouche_ref,
        profile=profile,
    )
    economic.status = FormulaStatus.PENDING_REVIEW  # en attente : une formule DEMO ne sera jamais validée
    economic.save(update_fields=["status"])

    # Ration en cours et distributions des 30 derniers jours
    ration = Ration.objects.create(
        farm=thies,
        name="Ration embouche Tabaski",
        formula=economic,
        group=embouche,
        start_date=today - timedelta(days=30),
        planned_as_fed_kg_per_animal_day=economic.as_fed_kg_day,
        is_demo=True,
        created_by=owner,
    )
    heads = len(fattening_animals)
    for offset in range(30, 0, -1):
        planned = economic.as_fed_kg_day * heads
        distributed = (planned * Decimal("1.02" if offset % 3 else "0.97")).quantize(Decimal("0.01"))
        record = FeedingRecord(
            farm=thies,
            ration=ration,
            group=embouche,
            fed_on=today - timedelta(days=offset),
            number_of_animals=heads,
            quantity_distributed_kg=distributed,
            is_demo=True,
            recorded_by=owner,
        )
        if (
            offset % 7 == 0
        ):  # refus pesés une fois par semaine seulement : la consommation n'est jamais supposée
            record.quantity_refused_kg = Decimal("0.40")
            record.quantity_consumed_kg = distributed - Decimal("0.40")
        FeedingRecordSerializer.compute_derived(record)
        record.save()
        summary.feeding_records += 1

    # Document technique DEMO (brouillon : un document DEMO n'est jamais validé)
    from django.core.files.base import ContentFile

    data = _make_pdf(DOCUMENT_PAGES)
    doc = TechnicalDocument(
        title=f"{PREFIX} Fiche pratique fictive : stockage des aliments",
        source=source,
        is_demo=True,
        description="Document de démonstration : contenu illustratif, non validé.",
        file_sha256=sha256_of(data),
        size_bytes=len(data),
        mime_type="application/pdf",
        uploaded_by=expert,
        created_by=expert,
        reference_date=today,
    )
    doc.file.save("demo-stockage-aliments.pdf", ContentFile(data), save=False)
    doc.save()
    process_document(doc, data)  # plein texte ; embeddings si configurés
    summary.documents = 1

    # Alertes calculées par les règles réelles
    for farm in farms.values():
        evaluate_farm(farm, today)
    evaluate_reviewers()
    summary.alerts = Alert.objects.filter(farm__in=farms.values(), status="OPEN").count()
    from formulations.models import FeedFormula

    summary.formulas = FeedFormula.objects.filter(farm__in=farms.values()).count()
    return summary
