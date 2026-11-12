export type FormulaMode = 'ECONOMIC' | 'BALANCED' | 'MANUAL' | 'TEMPLATE'
export type FormulaStatus = 'DRAFT' | 'REFUSED' | 'INFEASIBLE' | 'ESTIMATED' | 'PENDING_REVIEW' | 'VALIDATED' | 'REJECTED'

export interface FormulaItem {
  id: number
  ingredient: number
  ingredient_name: string
  /** Code de catégorie de l'ingrédient (pictogramme). */
  ingredient_category?: string | null
  inclusion_pct_dm: string | null
  inclusion_pct_as_fed: string | null
  quantity_dm_kg: string | null
  quantity_as_fed_kg: string | null
  price_per_kg_as_fed: string | null
  cost_per_day: string | null
}

export interface RequirementCheck {
  expression: 'DAILY_AMOUNT' | 'DIET_CONCENTRATION'
  min: number | null
  target: number | null
  max: number | null
  unit: string
  status: 'ok' | 'below' | 'above' | 'unknown'
}

export interface NutrientSupply {
  nutrient_id?: number
  code: string
  name: string
  system: string | null
  daily_amount: number | string | null
  daily_unit: string
  concentration_dm: number | string | null
  concentration_unit: string
  complete: boolean
  missing_for: string[]
  requirements?: RequirementCheck[]
}

export interface ConstraintCheck {
  constraint: string
  value: number | null
  unit: string
  min: number | null
  max: number | null
  status: 'ok' | 'below' | 'above'
}

export interface InfeasibilityItem {
  constraint: string
  side: 'min' | 'max'
  bound: number | null
  unit: string
  gap: number
  explanation: string
}

export interface FormulaSnapshot {
  kind?: 'manual_analysis'
  status?: 'ESTIMATED' | 'INFEASIBLE' | 'REFUSED'
  nutrients?: NutrientSupply[]
  constraints?: ConstraintCheck[]
  infeasibility?: InfeasibilityItem[]
  refusal_reasons?: string[]
  excluded_ingredients?: { ingredient_id: number; name: string; reasons: string[] }[]
  sources?: string[]
  disclaimer?: string
  reference?: { id: number; name: string; system: string; source: string | null; status: string; is_demo: boolean } | null
  solver_status?: string
  engine_version?: string
  /** Profil d'animal retenu pour le calcul (identifiants de nomenclature). */
  profile?: Record<string, number | string | null> & { head_count?: number | null }
}

export interface Formula {
  id: number
  farm: number
  name: string
  species: number
  reference: number | null
  mode: FormulaMode
  mode_label: string
  status: FormulaStatus
  status_label: string
  is_demo: boolean
  animal: number | null
  group: number | null
  season?: number | null
  season_name?: string | null
  /** Ration type validée dont la formule est issue. */
  template?: number | null
  template_name?: string | null
  /** Délai de vérification convenu. */
  review_requested_at?: string | null
  review_due_at?: string | null
  review_overdue?: boolean
  animal_weight_kg: string | null
  animal_age_months: string | null
  physiological_stage: number | null
  objective: number | null
  dm_intake_kg_day: string | null
  as_fed_kg_day: string | null
  cost_per_day: string | null
  cost_per_kg_as_fed: string | null
  currency: string
  items: FormulaItem[]
  result_snapshot: FormulaSnapshot
  warnings: string[]
  solver_status: string
  engine_version: string
  validated_by_email: string | null
  validated_at: string | null
  review_comment: string
  notes: string
  created_at: string
}

export interface CalculationPayload {
  farm: number
  name: string
  mode: 'ECONOMIC' | 'BALANCED'
  species?: number
  animal?: number | null
  group?: number | null
  reference?: number | null
  breed?: number | null
  category?: number | null
  physiological_stage?: number | null
  objective?: number | null
  animal_weight_kg?: string | null
  animal_age_months?: string | null
  ingredients: { ingredient: number; price_per_kg_as_fed?: string; available_kg_as_fed?: string }[]
  number_of_animals?: number
  duration_days?: number
  season?: number | null
  notes?: string
  save?: boolean
}

export interface RationTemplateItem {
  ingredient: number
  ingredient_name: string
  ingredient_category: string | null
  inclusion_pct_dm: string
}

export interface RationTemplate {
  id: number
  name: string
  species: number
  species_name: string
  category: number | null
  category_name: string | null
  physiological_stage: number | null
  physiological_stage_name: string | null
  objective: number | null
  objective_name: string | null
  season: number | null
  season_name: string | null
  weight_min_kg: string
  weight_max_kg: string
  dm_intake_kg_day: string
  conditions: string
  items: RationTemplateItem[]
  origin_formula: number | null
  is_demo: boolean
  status: 'DRAFT' | 'PENDING' | 'VALIDATED' | 'REJECTED'
  status_label: string
  validated_by_email: string | null
  validated_at: string | null
  validation_comment: string
  created_at: string
}
