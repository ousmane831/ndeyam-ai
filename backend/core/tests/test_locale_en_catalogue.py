"""
Catalogue anglais des messages du serveur (core/locale_en.py).

Vérifie la forme du catalogue (motifs valides, modèles cohérents, phrases réellement présentes dans le code),
puis que les messages RÉELLEMENT produits par le moteur de formulation, le profil des lots et les alertes
sont traduits, et enfin le comportement de bout en bout de l'API selon l'en-tête Accept-Language.
"""

import ast
import re
import string
from datetime import timedelta
from pathlib import Path

import pytest
from django.apps import apps
from django.utils import timezone

from core.i18n_messages import translate_text
from core.locale_en import EXACT, PATTERNS

pytestmark = pytest.mark.django_db

BACKEND = Path(__file__).resolve().parents[2]
SKIPPED_DIRS = {".venv", "migrations", "tests", "__pycache__", "node_modules"}
FRENCH_MARKERS = re.compile(r"[éèêàùçôî«»]|\b(?:le|la|les|des|du|une|est|pour|dans|aucun|aucune)\b")


def _source_literals():
    """Toutes les chaînes littérales du code applicatif (parties fixes des f-strings comprises)."""
    literals = set()
    for path in BACKEND.rglob("*.py"):
        if SKIPPED_DIRS & set(path.relative_to(BACKEND).parts):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                literals.add(node.value)
    return literals


def _english(text):
    translated = translate_text(text)
    assert translated != text, f"Message non traduit : {text!r}"
    return translated


# --- Forme du catalogue ---------------------------------------------------------------------------


def test_every_pattern_compiles_and_its_template_uses_exactly_its_groups():
    for pattern, template in PATTERNS:
        regex = re.compile(pattern)
        fields = {name for _, name, _, _ in string.Formatter().parse(template) if name}
        assert fields == set(regex.groupindex), (pattern, template)
        template.format(**{name: "x" for name in fields})  # accolades littérales bien doublées


def test_exact_keys_are_real_messages_of_the_code():
    """Chaque phrase du catalogue existe dans le code (pas de faute de frappe qui la rendrait inopérante)."""
    literals = _source_literals()
    literals |= {str(m._meta.verbose_name_plural) for m in apps.get_models()}
    missing = [key for key in EXACT if not any(key in literal for literal in literals)]
    assert not missing


def test_translations_are_not_empty_and_keep_numbers():
    assert all(value.strip() for value in EXACT.values())
    for key, value in EXACT.items():
        assert re.findall(r"\d+", key) == re.findall(r"\d+", value), key


# --- Moteur de formulation ------------------------------------------------------------------------


def _engine_results():
    from formulations.engine import (
        InclusionBound,
        IngredientInput,
        Mode,
        NutrientSpec,
        Problem,
        RequirementSpec,
        formulate,
    )
    from formulations.engine.types import Expression

    nutrients = {
        1: NutrientSpec(1, "PROT", "Protéines test", "g"),
        2: NutrientSpec(2, "ENER", "Énergie", "U"),
    }

    def ing(id_, name, dm=1000, prot=100, price=100.0, **kw):
        return IngredientInput(
            id=id_,
            name=name,
            dm_g_per_kg_as_fed=dm,
            composition_per_kg_dm={1: prot} if prot is not None else {},
            price_per_kg_as_fed=price,
            **kw,
        )

    def problem(ingredients, requirements=None, dmi=(1.0, 1.0), mode=Mode.ECONOMIC, bounds=()):
        return Problem(
            mode=mode,
            nutrients=nutrients,
            requirements=[RequirementSpec(1, Expression.DAILY_AMOUNT, min_value=200)]
            if requirements is None
            else requirements,
            ingredients=ingredients,
            dm_intake_min_kg=dmi[0],
            dm_intake_max_kg=dmi[1],
            inclusion_bounds=list(bounds),
        )

    both = frozenset({1, 2})
    return [
        # Refus : ni besoin, ni ingestion, ni ingrédient.
        formulate(problem([], requirements=[], dmi=(None, None))),
        # Exclusions (MS inconnue, valeur manquante, prix inconnu, disponibilité nulle) puis refus.
        formulate(
            problem(
                [
                    ing(1, "Son", dm=None),
                    ing(2, "Paille", prot=None, price=None),
                    ing(3, "Tourteau", max_as_fed_kg_per_day=0),
                ]
            )
        ),
        # Estimation : prix DEMO, prix inconnu, teneur de la ration, incorporation, disponibilité.
        formulate(
            problem(
                [ing(1, "A", price_is_demo=True), ing(2, "B", prot=300, price=None, max_as_fed_kg_per_day=5)],
                requirements=[
                    RequirementSpec(1, Expression.DAILY_AMOUNT, min_value=200),
                    RequirementSpec(1, Expression.DIET_CONCENTRATION, min_value=150, max_value=280),
                ],
                mode=Mode.BALANCED,
                bounds=[InclusionBound("Cereals", frozenset({1}), max_pct_dm=90)],
            )
        ),
        # Infaisable : besoins contradictoires (minimum et maximum à relâcher).
        formulate(
            problem(
                [ing(1, "A"), ing(2, "B", prot=300)],
                requirements=[
                    RequirementSpec(1, Expression.DAILY_AMOUNT, max_value=50),
                    RequirementSpec(1, Expression.DIET_CONCENTRATION, min_value=400),
                ],
                bounds=[InclusionBound("Fourrages", frozenset({1}), min_pct_dm=10, max_pct_dm=20)],
            )
        ),
        # Infaisable : disponibilités insuffisantes pour l'ingestion.
        formulate(
            problem(
                [ing(1, "A", max_as_fed_kg_per_day=0.2), ing(2, "B", prot=300, max_as_fed_kg_per_day=0.2)],
                bounds=[InclusionBound("Fourrages", both, min_pct_dm=10)],
            )
        ),
        # Infaisable : teneur maximale dépassée par le seul ingrédient.
        formulate(
            problem(
                [ing(1, "A")],
                requirements=[RequirementSpec(1, Expression.DIET_CONCENTRATION, max_value=50)],
                dmi=(0.5, 0.5),
            )
        ),
    ]


def _all_constraint_labels():
    """Libellés et unités de chaque type de contrainte que le solveur sait poser."""
    import pulp

    from formulations.engine import (
        InclusionBound,
        IngredientInput,
        Mode,
        NutrientSpec,
        Problem,
        RequirementSpec,
    )
    from formulations.engine.solver import _constraint_rows
    from formulations.engine.types import Expression

    problem = Problem(
        mode=Mode.ECONOMIC,
        nutrients={1: NutrientSpec(1, "MAT", "Matière azotée totale", "g")},
        requirements=[
            RequirementSpec(1, Expression.DAILY_AMOUNT, min_value=1),
            RequirementSpec(1, Expression.DIET_CONCENTRATION, min_value=1),
        ],
        ingredients=[IngredientInput(1, "A", 900, {1: 100}, 100, max_as_fed_kg_per_day=2)],
        dm_intake_min_kg=1,
        dm_intake_max_kg=2,
        inclusion_bounds=[InclusionBound("Cereals", frozenset({1}), max_pct_dm=50)],
    )
    model = pulp.LpProblem("labels", pulp.LpMinimize)
    rows = _constraint_rows(problem, {1: model.add_variable("x_1", lowBound=0)})
    assert len(rows) == 5
    return [text for row in rows for text in (row[1], row[6])]


def test_every_engine_message_is_translated():
    results = _engine_results()
    assert [r.status for r in results] == ["REFUSED", "REFUSED", "ESTIMATED"] + ["INFEASIBLE"] * 3
    explanations = [row["explanation"] for r in results for row in r.infeasibility]
    assert any(e.startswith("Minimum de") for e in explanations)
    assert any(e.startswith("Maximum de") for e in explanations)
    texts = [results[0].solver_status, results[0].disclaimer, *_all_constraint_labels()]
    for result in results:
        texts += result.refusal_reasons + result.warnings
        texts += [reason for excluded in result.excluded_ingredients for reason in excluded["reasons"]]
        for row in result.constraints + result.infeasibility:
            texts += [row["constraint"], row["unit"]]
        texts += [row["explanation"] for row in result.infeasibility]
        for row in result.nutrients:
            texts += [row["daily_unit"], row["concentration_unit"]]
            texts += [req["unit"] for req in row["requirements"]]
    assert len(texts) > 30
    for text in texts:
        assert not FRENCH_MARKERS.search(_english(text).replace("“", "").replace("”", "")), text


def test_engine_messages_read_naturally_in_english():
    assert (
        translate_text(
            "« Son » exclu : teneur en matière sèche inconnue ; prix inconnu (indispensable en mode "
            "économique)."
        )
        == "“Son” excluded: dry matter content unknown ; price unknown "
        "(required in economic mode)."
    )
    assert translate_text(
        "« Paille » exclu : valeur(s) validée(s) inconnue(s) pour : MAT, Ca ; quantité disponible nulle."
    ) == ("“Paille” excluded: validated value(s) unknown for: MAT, Ca ; no quantity available.")
    assert translate_text("MAT (apport journalier)") == "MAT (daily supply)"
    assert translate_text("Incorporation : Céréales") == "Inclusion: Céréales"
    assert translate_text("g/kg MS") == "g/kg DM"
    assert translate_text(
        "Minimum de 0.5 kg MS/jour impossible à atteindre : il manque environ 0.1 kg MS/jour."
    ) == ("Minimum of 0.5 kg DM/day cannot be reached: about 0.1 kg DM/day short.")


# --- Profil d'un lot ------------------------------------------------------------------------------


def test_group_profile_notes_are_translated(farm, ovin):
    from animals.models import Animal, AnimalGroup
    from animals.services import group_profile

    empty = AnimalGroup.objects.create(farm=farm, name="Lot vide", species=ovin)
    group = AnimalGroup.objects.create(farm=farm, name="Lot mixte", species=ovin)
    categories = list(ovin.categories.all()[:2])
    for n, category in enumerate(categories):
        Animal.objects.create(
            farm=farm,
            species=ovin,
            tag_number=f"SN-L{n}",
            sex="F",
            group=group,
            category=category,
            initial_weight_kg=30 + n,
        )
    notes = group_profile(empty)["notes"] + group_profile(group)["notes"]
    assert len(notes) == 3
    english = [_english(note) for note in notes]
    assert english[0] == "Group “Lot vide” has no animals present."
    assert english[1].startswith("Mixed group, category: most frequent value used (")
    assert english[2] == "Average group weight: 30,50 kg (2 animal(s) weighed out of 2)."


def test_animal_history_labels_are_translated():
    assert translate_text("Ration « Embouche » (En cours)") == "Ration “Embouche” (Ongoing)"
    assert (
        translate_text("Distribution : 2.5 kg (consommation non mesurée)")
        == "Feeding: 2.5 kg (intake not measured)"
    )
    assert translate_text("Distribution : 2.5 kg (2.0 kg consommés)") == "Feeding: 2.5 kg (2.0 kg consumed)"
    assert translate_text("Observation (État de santé observé (non diagnostique))") == (
        "Observation (Observed health status (not a diagnosis))"
    )


# --- Alertes --------------------------------------------------------------------------------------


def test_alert_titles_and_messages_are_translated(farm, animal, ovin, validated_kwargs, ingredient, expert):
    from alerts.engine import evaluate_farm, evaluate_reviewers
    from alerts.models import Alert
    from growth.models import GrowthMonitoringRange, Weighing

    today = timezone.localdate()
    animal.registered_on = today - timedelta(days=100)
    animal.save()
    Weighing.objects.create(animal=animal, weight_kg=20, weighed_on=today - timedelta(days=60))
    Weighing.objects.create(animal=animal, weight_kg=21, weighed_on=today - timedelta(days=40))
    GrowthMonitoringRange.objects.create(
        name="Range A", species=ovin, adg_min_g=100, adg_max_g=250, **validated_kwargs
    )
    ingredient(name="Ingrédient en attente", status="PENDING")
    evaluate_farm(farm)
    evaluate_reviewers()
    alerts = list(Alert.objects.all())
    assert {a.alert_type for a in alerts} >= {
        "WEIGHING_REMINDER",
        "MISSING_DATA",
        "GROWTH_OUT_OF_RANGE",
        "REFERENCE_TO_VALIDATE",
    }
    for alert in alerts:
        for text in (
            alert.title,
            alert.message,
            alert.get_alert_type_display(),
            alert.get_severity_display(),
        ):
            english = _english(text) if text not in ("Information", "Important") else text
            english = english.replace(str(validated_kwargs["source"]), "")
            assert not FRENCH_MARKERS.search(english.replace("“", "").replace("”", "")), text
    growth = next(a for a in alerts if a.alert_type == "GROWTH_OUT_OF_RANGE")
    assert "below the range “Range A”" in translate_text(growth.message)
    assert translate_text(growth.message).endswith("consult a veterinarian.")


# --- Bout en bout : calcul d'une formule par l'API ------------------------------------------------


@pytest.fixture
def calc(farm, breeder, ovin, ingredient, nutrient, make_composition, validated_kwargs, client_for):
    from nutrition.models import (
        IngredientPrice,
        NutritionalReference,
        NutritionalRequirement,
        NutritionSystem,
    )

    reference = NutritionalReference.objects.create(
        name="Référence contrôlée",
        species=ovin,
        system=NutritionSystem.objects.get(code="INRA"),
        dm_intake_min_kg_day=1,
        dm_intake_max_kg_day=1,
        **validated_kwargs,
    )
    NutritionalRequirement.objects.create(
        reference=reference, nutrient=nutrient("MAT"), expression="DAILY_AMOUNT", min_value=200
    )
    a, b, c = (ingredient(name=n) for n in ("Ingrédient A", "Ingrédient B", "Ingrédient sans données"))
    for item, mat, price in ((a, 100, 100), (b, 300, 300)):
        make_composition(item, nutrient("MS"), 1000)
        make_composition(item, nutrient("MAT"), mat)
        IngredientPrice.objects.create(farm=farm, ingredient=item, price_per_kg_as_fed=price)
    client = client_for(breeder)

    def post(ingredients, **headers):
        payload = {
            "farm": farm.pk,
            "name": "Calcul test",
            "mode": "ECONOMIC",
            "species": ovin.pk,
            "save": False,
            "ingredients": [{"ingredient": i.pk} for i in ingredients],
        }
        response = client.post("/api/v1/formulas/calculate/", payload, format="json", **headers)
        assert response.status_code == 200, response.json()
        return response.json()["result"]

    return {"post": post, "a": a, "b": b, "c": c}


def test_calculation_answers_in_english_only_when_asked(calc):
    ingredients = [calc["a"], calc["b"], calc["c"]]
    fr = calc["post"](ingredients)
    en = calc["post"](ingredients, HTTP_ACCEPT_LANGUAGE="en")
    assert fr["status"] == en["status"] == "ESTIMATED"
    assert "Référence retenue automatiquement : « Référence contrôlée »." in fr["warnings"]
    assert any(w.startswith("« Ingrédient sans données » exclu : ") for w in fr["warnings"])
    assert en["warnings"][0] == "Reference selected automatically: “Référence contrôlée”."
    assert en["warnings"][1] == (
        "“Ingrédient sans données” excluded: dry matter content unknown ; "
        "validated value(s) unknown for: MAT ; "
        "price unknown (required in economic mode)."
    )
    assert en["excluded_ingredients"][0]["name"] == "Ingrédient sans données"  # donnée saisie : intacte
    assert [c["constraint"] for c in en["constraints"]] == ["Dry matter intake", "MAT (daily supply)"]
    assert [c["constraint"] for c in fr["constraints"]] == [
        "Ingestion de matière sèche",
        "MAT (apport journalier)",
    ]
    assert en["disclaimer"].startswith("Mathematical estimate calculated from validated data only.")
    assert fr["disclaimer"].startswith("Estimation mathématique")


def test_refused_calculation_reasons_in_english(calc):
    fr = calc["post"]([calc["c"]])
    en = calc["post"]([calc["c"]], HTTP_ACCEPT_LANGUAGE="en")
    assert fr["status"] == en["status"] == "REFUSED"
    assert fr["refusal_reasons"] == [
        "Aucun ingrédient proposé ne dispose de toutes les données validées nécessaires."
    ]
    assert en["refusal_reasons"] == ["None of the offered ingredients has all the required validated data."]
    assert en["solver_status"] == "not run" and fr["solver_status"] == "non lancé"
