"""
Outils métier mis à disposition du LLM.

Chaque outil :
- s'exécute avec les droits de l'utilisateur (exploitations accessibles uniquement) ;
- renvoie des données réelles issues de la base, du moteur nutritionnel ou de la base documentaire ;
- déclare sa provenance (`database`, `engine`, `document`), affichée sous la réponse.
Aucun outil ne calcule de ration : `get_formula_result` lit le résultat enregistré par le moteur.
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from .llm import ToolSpec


class ToolError(Exception):
    pass


def _obj(properties=None, required=None):
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


TOOL_SPECS = [
    ToolSpec("list_my_farms", "Liste les exploitations accessibles à l'utilisateur (id, nom, rôle).", _obj()),
    ToolSpec(
        "find_animals",
        "Recherche des animaux présents par numéro ou nom. Renvoie id, numéro, nom, lot, dernier poids.",
        _obj(
            {
                "search": {"type": "string", "description": "Numéro ou nom (vide = tous)"},
                "farm_id": {"type": "integer"},
            }
        ),
    ),
    ToolSpec(
        "get_animal_growth",
        "Évolution du poids et GMD d'un animal (calculés à partir des pesées enregistrées).",
        _obj({"animal_id": {"type": "integer"}}, ["animal_id"]),
    ),
    ToolSpec(
        "list_groups",
        "Liste les lots (troupeaux) avec le nombre d'animaux présents.",
        _obj({"farm_id": {"type": "integer"}}),
    ),
    ToolSpec(
        "get_feeding_cost",
        "Coût estimé et quantités des distributions enregistrées sur une période, pour un lot, "
        "un animal ou toute l'exploitation.",
        _obj(
            {
                "group_id": {"type": "integer"},
                "animal_id": {"type": "integer"},
                "farm_id": {"type": "integer"},
                "days": {"type": "integer", "description": "Période en jours (défaut 30)"},
            }
        ),
    ),
    ToolSpec(
        "list_formulas",
        "Liste les formules enregistrées (calculées ou saisies) avec leur statut et leur coût.",
        _obj({"status": {"type": "string"}, "farm_id": {"type": "integer"}}),
    ),
    ToolSpec(
        "get_formula_result",
        "Résultat détaillé d'une formule tel que calculé par le moteur nutritionnel : statut, "
        "raisons d'un refus, contraintes bloquantes, ingrédients, apports, avertissements, sources.",
        _obj({"formula_id": {"type": "integer"}}, ["formula_id"]),
    ),
    ToolSpec(
        "check_formulation_readiness",
        "Indique quelles données validées manquent pour pouvoir calculer une formule "
        "(références nutritionnelles, compositions, prix).",
        _obj({"farm_id": {"type": "integer"}}),
    ),
    ToolSpec(
        "search_documents",
        "Recherche dans les documents techniques validés. Renvoie des extraits avec leur citation.",
        _obj({"query": {"type": "string"}}, ["query"]),
    ),
    ToolSpec(
        "list_open_alerts",
        "Alertes et rappels ouverts (avec leur explication).",
        _obj({"farm_id": {"type": "integer"}}),
    ),
]


def _s(value):
    if isinstance(value, Decimal):
        return str(value)
    return value


class ToolContext:
    """Exécute les outils pour un utilisateur donné et collecte la provenance des informations."""

    def __init__(self, user, farm=None):
        from farms.access import readable_farms

        self.user = user
        self.farms = readable_farms(user)
        if farm is not None:
            self.farms = self.farms.filter(pk=farm.pk)
        self.provenance = []

    def _farms(self, farm_id=None):
        if farm_id is None:
            return self.farms
        farms = self.farms.filter(pk=farm_id)
        if not farms.exists():
            raise ToolError("Exploitation introuvable ou non accessible.")
        return farms

    def _cite(self, kind, label, **extra):
        entry = {"type": kind, "label": label, **extra}
        if entry not in self.provenance:
            self.provenance.append(entry)

    def execute(self, name, arguments):
        """Retourne (texte JSON, succès). Les erreurs sont renvoyées au modèle, jamais masquées."""
        handler = getattr(self, f"tool_{name}", None)
        if handler is None or name not in {t.name for t in TOOL_SPECS}:
            return json.dumps({"erreur": f"Outil inconnu : {name}"}, ensure_ascii=False), False
        try:
            data = handler(**(arguments or {}))
        except ToolError as exc:
            return json.dumps({"erreur": str(exc)}, ensure_ascii=False), False
        except TypeError:
            return json.dumps({"erreur": "Arguments invalides pour cet outil."}, ensure_ascii=False), False
        return json.dumps(data, ensure_ascii=False, default=str), True

    # --- Outils -----------------------------------------------------------------------------

    def tool_list_my_farms(self):
        from farms.access import membership_for

        self._cite("database", "Exploitations")
        rows = []
        for farm in self.farms:
            membership = membership_for(self.user, farm)
            rows.append(
                {
                    "id": farm.pk,
                    "nom": farm.name,
                    "region": farm.region,
                    "demo": farm.is_demo,
                    "role": membership.get_role_display() if membership else "Administrateur",
                }
            )
        return {"exploitations": rows}

    def tool_find_animals(self, search="", farm_id=None):
        from animals.models import Animal, AnimalStatus

        qs = Animal.objects.filter(farm__in=self._farms(farm_id), status=AnimalStatus.ACTIVE).select_related(
            "group", "breed"
        )
        if search:
            qs = qs.filter(Q(tag_number__icontains=search) | Q(name__icontains=search))
        self._cite("database", "Animaux enregistrés")
        rows = []
        for a in qs.order_by("tag_number")[:20]:
            last = a.weighings.order_by("-weighed_on").first()
            rows.append(
                {
                    "id": a.pk,
                    "numero": a.tag_number,
                    "nom": a.name,
                    "race": a.breed.name if a.breed else None,
                    "sexe": a.get_sex_display(),
                    "lot": a.group.name if a.group else None,
                    "dernier_poids_kg": _s(last.weight_kg) if last else None,
                    "date_dernier_poids": last.weighed_on if last else None,
                }
            )
        return {"animaux": rows, "total": qs.count(), "limite_affichee": 20}

    def _animal(self, animal_id):
        from animals.models import Animal

        animal = Animal.objects.filter(farm__in=self.farms, pk=animal_id).first()
        if animal is None:
            raise ToolError("Animal introuvable ou non accessible.")
        return animal

    def tool_get_animal_growth(self, animal_id):
        from growth.services import animal_growth

        animal = self._animal(animal_id)
        growth = animal_growth(animal)
        self._cite("database", f"Pesées de l'animal {animal.tag_number}")
        return {
            "animal": animal.tag_number,
            "points": growth["points"],
            "intervalles": growth["intervals"],
            "gmd_global": growth["overall"],
            "raison_si_indisponible": growth["unavailable_reason"],
            "formule": growth["formula"],
            "plage_de_suivi_validee": growth["monitoring_range"],
            "position_par_rapport_a_la_plage": growth["latest_vs_range"],
            "note": growth["monitoring_note"],
        }

    def tool_list_groups(self, farm_id=None):
        from animals.models import AnimalGroup, AnimalStatus

        self._cite("database", "Lots")
        qs = AnimalGroup.objects.filter(farm__in=self._farms(farm_id)).annotate(
            presents=Count("animals", filter=Q(animals__status=AnimalStatus.ACTIVE))
        )
        return {
            "lots": [
                {"id": g.pk, "nom": g.name, "animaux_presents": g.presents, "actif": g.is_active} for g in qs
            ]
        }

    def tool_get_feeding_cost(self, group_id=None, animal_id=None, farm_id=None, days=30):
        from feeding.models import FeedingRecord

        days = max(1, min(int(days or 30), 365))
        qs = FeedingRecord.objects.filter(
            farm__in=self._farms(farm_id), fed_on__gte=timezone.localdate() - timedelta(days=days)
        )
        target = "toute l'exploitation"
        if group_id:
            qs = qs.filter(group_id=group_id)
            target = f"lot #{group_id}"
        if animal_id:
            qs = qs.filter(animal=self._animal(animal_id))
            target = f"animal #{animal_id}"
        agg = qs.aggregate(
            cout=Sum("estimated_cost"),
            distribue=Sum("quantity_distributed_kg"),
            consomme=Sum("quantity_consumed_kg"),
        )
        self._cite("database", "Historique alimentaire")
        return {
            "periode_jours": days,
            "cible": target,
            "distributions": qs.count(),
            "cout_estime_fcfa": _s(agg["cout"]),
            "distribue_kg_brut": _s(agg["distribue"]),
            "consomme_mesure_kg_brut": _s(agg["consomme"]),
            "distributions_sans_cout_connu": qs.filter(estimated_cost__isnull=True).count(),
            "distributions_avec_consommation_mesuree": qs.filter(quantity_consumed_kg__isnull=False).count(),
            "note": "Coût estimé = quantité distribuée × coût par kg de la formule ; "
            "la consommation n'est jamais supposée.",
        }

    def tool_list_formulas(self, status=None, farm_id=None):
        from formulations.models import FeedFormula

        qs = FeedFormula.objects.filter(farm__in=self._farms(farm_id)).order_by("-created_at")
        if status:
            qs = qs.filter(status=status)
        self._cite("database", "Formules enregistrées")
        return {
            "formules": [
                {
                    "id": f.pk,
                    "nom": f.name,
                    "mode": f.get_mode_display(),
                    "statut": f.get_status_display(),
                    "cout_par_animal_par_jour_fcfa": _s(f.cost_per_day),
                    "date": f.created_at.date(),
                    "demo": f.is_demo,
                }
                for f in qs[:15]
            ]
        }

    def tool_get_formula_result(self, formula_id):
        from formulations.models import FeedFormula

        formula = (
            FeedFormula.objects.filter(farm__in=self.farms, pk=formula_id)
            .prefetch_related("items__ingredient")
            .first()
        )
        if formula is None:
            raise ToolError("Formule introuvable ou non accessible.")
        snap = formula.result_snapshot or {}
        self._cite("engine", f"Moteur nutritionnel — formule « {formula.name} »", formula_id=formula.pk)
        return {
            "nom": formula.name,
            "mode": formula.get_mode_display(),
            "statut": formula.get_status_display(),
            "demo": formula.is_demo,
            "valide_par_un_expert": formula.status == "VALIDATED",
            "raisons_du_refus": snap.get("refusal_reasons", []),
            "contraintes_bloquantes": snap.get("infeasibility", []),
            "ingredients": [
                {
                    "nom": i.ingredient.name,
                    "pct_ms": _s(i.inclusion_pct_dm),
                    "kg_brut_par_jour": _s(i.quantity_as_fed_kg),
                    "cout_par_jour": _s(i.cost_per_day),
                }
                for i in formula.items.all()
            ],
            "ms_kg_par_jour": _s(formula.dm_intake_kg_day),
            "cout_par_jour_fcfa": _s(formula.cost_per_day),
            "apports": snap.get("nutrients", []),
            "verification_des_contraintes": snap.get("constraints", []),
            "ingredients_exclus": snap.get("excluded_ingredients", []),
            "avertissements": formula.warnings,
            "reference": snap.get("reference"),
            "sources": snap.get("sources", []),
            "avertissement_general": snap.get("disclaimer"),
        }

    def tool_check_formulation_readiness(self, farm_id=None):
        from governance.models import ValidationStatus
        from nutrition.models import IngredientComposition, IngredientPrice, NutritionalReference

        farms = self._farms(farm_id)
        refs = NutritionalReference.objects.usable_for_engine()
        with_intake = refs.exclude(dm_intake_min_kg_day__isnull=True, dm_intake_max_kg_day__isnull=True)
        with_dm = (
            IngredientComposition.objects.usable_for_engine()
            .filter(nutrient__category="DRY_MATTER")
            .values("ingredient")
            .distinct()
        )
        priced = IngredientPrice.objects.filter(farm__in=farms, is_demo=False).values("ingredient").distinct()
        pending = NutritionalReference.objects.filter(status=ValidationStatus.PENDING).count()
        missing = []
        if not with_intake.exists():
            missing.append(
                "Aucune référence nutritionnelle validée avec bornes d'ingestion de matière sèche."
            )
        if not with_dm.exists():
            missing.append("Aucun ingrédient n'a de teneur en matière sèche validée.")
        if not priced.exists():
            missing.append(
                "Aucun prix d'ingrédient enregistré dans l'exploitation (indispensable en mode économique)."
            )
        self._cite("database", "Référentiel nutritionnel et prix")
        return {
            "references_validees": refs.count(),
            "references_avec_ingestion_ms": with_intake.count(),
            "references_en_attente": pending,
            "ingredients_avec_ms_validee": with_dm.count(),
            "ingredients_avec_prix": priced.count(),
            "manques": missing,
            "calcul_possible": not missing,
        }

    def tool_search_documents(self, query):
        from knowledge_base.search import search

        result = search(query, k=4)
        for hit in result["results"]:
            self._cite("document", hit["citation"], document_id=hit["document_id"], pages=hit["pages"])
        return {
            "methode": result["method"],
            "avertissements": result["warnings"],
            "extraits": [{"citation": h["citation"], "texte": h["excerpt"]} for h in result["results"]],
        }

    def tool_list_open_alerts(self, farm_id=None):
        from alerts.models import Alert

        qs = Alert.objects.filter(
            Q(farm__in=self._farms(farm_id)) | Q(recipient=self.user), status__in=["OPEN", "ACKNOWLEDGED"]
        ).order_by("-created_at")
        self._cite("database", "Alertes")
        return {
            "alertes": [
                {
                    "titre": a.title,
                    "type": a.get_alert_type_display(),
                    "niveau": a.get_severity_display(),
                    "message": a.message,
                    "regle": a.rule_code,
                }
                for a in qs[:15]
            ],
            "total_ouvertes": qs.count(),
        }
