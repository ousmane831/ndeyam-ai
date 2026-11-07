"""Structures de données du moteur (unités explicites dans chaque nom de champ)."""

from dataclasses import dataclass, field
from enum import StrEnum

ENGINE_VERSION = "1.0.0"


class Mode(StrEnum):
    ECONOMIC = "ECONOMIC"  # coût minimal sous contraintes validées
    BALANCED = "BALANCED"  # au plus près des cibles configurées par les experts, coût en second critère


class Expression(StrEnum):
    DAILY_AMOUNT = "DAILY_AMOUNT"  # quantité par animal et par jour
    DIET_CONCENTRATION = "DIET_CONCENTRATION"  # teneur de la ration, par kg de MS


@dataclass(frozen=True)
class NutrientSpec:
    id: int
    code: str
    name: str
    amount_unit: str  # g, UFL, Mcal…
    system: str | None = None  # None = nutriment universel

    @property
    def concentration_unit(self):
        return f"{self.amount_unit}/kg MS"

    @property
    def daily_unit(self):
        return f"{self.amount_unit}/jour"


@dataclass(frozen=True)
class RequirementSpec:
    nutrient_id: int
    expression: Expression
    min_value: float | None = None
    target_value: float | None = None
    max_value: float | None = None


@dataclass
class IngredientInput:
    id: int
    name: str
    dm_g_per_kg_as_fed: float | None  # teneur en MS validée (None = inconnue)
    # nutrient_id -> valeur par kg de MS (valeurs validées uniquement)
    composition_per_kg_dm: dict[int, float]
    price_per_kg_as_fed: float | None = None
    currency: str = "XOF"
    max_as_fed_kg_per_day: float | None = None  # disponibilité ramenée à un animal et un jour
    sources: dict[int, str] = field(default_factory=dict)  # nutrient_id -> source citée
    price_is_demo: bool = False

    @property
    def dm_fraction(self):
        return self.dm_g_per_kg_as_fed / 1000.0 if self.dm_g_per_kg_as_fed else None

    @property
    def price_per_kg_dm(self):
        if self.price_per_kg_as_fed is None or not self.dm_fraction:
            return None
        return self.price_per_kg_as_fed / self.dm_fraction


@dataclass(frozen=True)
class InclusionBound:
    label: str
    ingredient_ids: frozenset[int]
    min_pct_dm: float | None = None
    max_pct_dm: float | None = None
    source: str = ""


@dataclass
class Problem:
    mode: Mode
    nutrients: dict[int, NutrientSpec]
    requirements: list[RequirementSpec]
    ingredients: list[IngredientInput]
    dm_intake_min_kg: float | None
    dm_intake_max_kg: float | None
    inclusion_bounds: list[InclusionBound] = field(default_factory=list)
    reference_label: str = ""
    reference_source: str = ""
    is_demo: bool = False


@dataclass
class FormulationResult:
    status: str  # ESTIMATED | INFEASIBLE | REFUSED
    mode: str
    solver_status: str = ""
    items: list[dict] = field(default_factory=list)
    dm_intake_kg_day: float | None = None
    as_fed_kg_day: float | None = None
    cost_per_day: float | None = None
    cost_per_kg_as_fed: float | None = None
    currency: str = "XOF"
    nutrients: list[dict] = field(default_factory=list)
    constraints: list[dict] = field(default_factory=list)
    infeasibility: list[dict] = field(default_factory=list)
    refusal_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    excluded_ingredients: list[dict] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    engine_version: str = ENGINE_VERSION
    disclaimer: str = (
        "Estimation mathématique calculée à partir des seules données validées. "
        "Elle ne constitue pas une recommandation nutritionnelle validée "
        "tant qu'un expert ne l'a pas vérifiée."
    )

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}
