"""
Cas de référence du moteur de formulation, calculés par le moteur Python (PuLP / CBC).

Le moteur hors ligne de l'interface (frontend/src/features/offline/engine.ts) doit retrouver le même
statut, le même coût optimal et la même ingestion sur chacun de ces cas (test Vitest `engine.test.ts`).
À relancer après toute modification du moteur :

    python scripts/export_engine_cases.py

Les jeux synthétiques sont arbitraires (sans portée nutritionnelle) ; les cas « pack » reprennent les
problèmes préparés du paquet hors ligne DEMO (frontend/src/features/offline/demo-pack.fixture.json).
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from formulations.engine import (  # noqa: E402
    InclusionBound,
    IngredientInput,
    Mode,
    NutrientSpec,
    Problem,
    RequirementSpec,
    formulate,
)
from formulations.engine.types import Expression  # noqa: E402

OUT_DIR = ROOT.parent / "frontend" / "src" / "features" / "offline"
NUTRIENTS = {
    1: NutrientSpec(1, "PROT", "Protéines test", "g"),
    2: NutrientSpec(2, "ENER", "Énergie test", "U", system="TEST"),
    3: NutrientSpec(3, "CA", "Calcium test", "g"),
}


def ing(id_, name, dm, comp, price, **kw):
    return IngredientInput(
        id=id_, name=name, dm_g_per_kg_as_fed=dm, composition_per_kg_dm=comp, price_per_kg_as_fed=price, **kw
    )


def prob(ingredients, requirements, mode=Mode.ECONOMIC, dmi=(1.0, 1.0), bounds=()):
    return Problem(
        mode=mode,
        nutrients=NUTRIENTS,
        requirements=requirements,
        ingredients=ingredients,
        dm_intake_min_kg=dmi[0],
        dm_intake_max_kg=dmi[1],
        inclusion_bounds=list(bounds),
        reference_label="Référence test",
    )


DAILY, CONC = Expression.DAILY_AMOUNT, Expression.DIET_CONCENTRATION
A = lambda: ing(1, "A", 1000, {1: 100, 2: 0.9, 3: 2}, 100)  # noqa: E731
B = lambda: ing(2, "B", 1000, {1: 300, 2: 1.1, 3: 6}, 300)  # noqa: E731
C = lambda: ing(3, "C", 880, {1: 450, 2: 1.0, 3: 3}, 260)  # noqa: E731
D = lambda: ing(4, "D", 900, {1: 60, 2: 0.6, 3: 4}, 40)  # noqa: E731
SYNTHETIC = {
    "economique_simple": prob([A(), B()], [RequirementSpec(1, DAILY, 200)]),
    "economique_teneur_et_plafond": prob(
        [A(), B(), C(), D()],
        [RequirementSpec(1, CONC, 150, None, 260), RequirementSpec(3, DAILY, 3.5, None, 8)],
        dmi=(1.1, 1.4),
        bounds=[
            InclusionBound("C plafonné", frozenset({3}), None, 20),
            InclusionBound("D minimum", frozenset({4}), 10, None),
        ],
    ),
    "equilibre_cibles": prob(
        [A(), B(), C(), D()],
        [RequirementSpec(1, DAILY, 150, 210, 260), RequirementSpec(2, CONC, 0.8, 0.95, 1.05)],
        mode=Mode.BALANCED,
        dmi=(1.0, 1.3),
    ),
    "disponibilite_limitee": prob(
        [A(), ing(2, "B", 1000, {1: 300, 2: 1.1, 3: 6}, 300, max_as_fed_kg_per_day=0.3), C()],
        [RequirementSpec(1, DAILY, 250)],
    ),
    "impossible": prob([A(), D()], [RequirementSpec(1, DAILY, 250)]),
    "refus_sans_besoin": prob([A(), B()], []),
    "exclusions": prob(
        [
            A(),
            ing(5, "Sans MS", None, {1: 200}, 50),
            ing(6, "Sans prix", 900, {1: 200}, None),
            ing(7, "Sans PROT", 900, {2: 1}, 10),
        ],
        [RequirementSpec(1, DAILY, 90)],
    ),
}


def pack_cases():
    from formulations.engine_service import deserialize_problem

    pack = json.loads((OUT_DIR / "demo-pack.fixture.json").read_text(encoding="utf-8"))
    cases = {}
    for ref in pack["references"]:
        all_ids = [i["id"] for i in ref["problem"]["ingredients"]]
        for mode in ("ECONOMIC", "BALANCED"):
            for label, ids in (("tous", all_ids), ("sans_premier", all_ids[1:])):
                data = json.loads(json.dumps(ref["problem"]))
                data["mode"] = mode
                data["ingredients"] = [i for i in data["ingredients"] if i["id"] in ids]
                data["inclusion_bounds"] = [
                    {**b, "ingredient_ids": [i for i in b["ingredient_ids"] if i in ids]}
                    for b in data["inclusion_bounds"]
                    if set(b["ingredient_ids"]) & set(ids)
                ]
                cases[f"pack_{ref['id']}_{mode.lower()}_{label}"] = (deserialize_problem(data), data)
    return cases


def expected(result):
    return {
        "status": result.status,
        "dm_intake_kg_day": result.dm_intake_kg_day,
        "cost_per_day": result.cost_per_day,
        "items": {str(i["ingredient_id"]): i["quantity_dm_kg"] for i in result.items},
        "excluded": sorted(e["ingredient_id"] for e in result.excluded_ingredients),
        "constraints_ok": all(c["status"] == "ok" for c in result.constraints)
        if result.constraints
        else None,
    }


def main():
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    django.setup()
    from formulations.engine_service import serialize_problem

    cases = []
    for name, problem in SYNTHETIC.items():
        data = serialize_problem(problem)
        cases.append({"name": name, "problem": data, "expected": expected(formulate(problem))})
    for name, (problem, data) in pack_cases().items():
        cases.append({"name": name, "problem": data, "expected": expected(formulate(problem))})
    out = OUT_DIR / "engine-cases.fixture.json"
    out.write_text(json.dumps(cases, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(cases)} cas écrits dans {out}")
    for c in cases:
        e = c["expected"]
        print(f"  {c['name']:45} {e['status']:10} coût={e['cost_per_day']} MS={e['dm_intake_kg_day']}")


if __name__ == "__main__":
    main()
