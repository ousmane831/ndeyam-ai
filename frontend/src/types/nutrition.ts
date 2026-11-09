export type ValidationStatus = 'DRAFT' | 'PENDING' | 'VALIDATED' | 'REJECTED'
export type WorkflowAction = 'submit' | 'validate' | 'reject' | 'revert'

export interface SourceRef {
  id: number
  title: string
  is_demo: boolean
}

export interface ValidatedFields {
  source: SourceRef | null
  reference_date: string | null
  is_demo: boolean
  status: ValidationStatus
  status_label: string
  validated_by_email: string | null
  validated_at: string | null
  validation_comment: string
}

export interface Nutrient {
  id: number
  code: string
  name: string
  category: string
  category_label: string
  amount_unit: string
  basis: 'DM' | 'AS_FED'
  unit_label: string
  system: number | null
  system_code: string | null
}

export interface NutritionSystem {
  id: number
  code: string
  name: string
  version: string
}

export interface IngredientCategory {
  id: number
  code: string
  name: string
}

export interface Ingredient extends ValidatedFields {
  id: number
  name: string
  local_names: string
  category: number
  category_name: string
  description: string
  farm: number | null
  scope: 'catalog' | 'private'
  observations: string
  is_active: boolean
  created_at: string
  /** Teneur en matière sèche utilisable par le moteur (liste uniquement). */
  ready_for_engine?: boolean | null
}

export interface Composition extends ValidatedFields {
  id: number
  ingredient: number
  ingredient_name: string
  nutrient: number
  nutrient_code: string
  nutrient_name: string
  system_code: string | null
  value: string
  unit_label: string
  analysis_method: string
  sample_origin: string
  notes: string
}

export interface CompositionRow {
  nutrient: Nutrient
  known: boolean
  validated_value: string | null
  values: Composition[]
}

export interface IngredientDetail extends Ingredient {
  composition_table: CompositionRow[]
}

export interface IngredientPrice {
  id: number
  farm: number
  ingredient: number
  ingredient_name: string
  price_per_kg_as_fed: string
  currency: string
  valid_from: string
  supplier: string
  location: string
  quantity_available_kg: string | null
  notes: string
  is_demo: boolean
}

export interface Requirement {
  id: number
  reference: number
  nutrient: number
  nutrient_code: string
  nutrient_name: string
  expression: 'DAILY_AMOUNT' | 'DIET_CONCENTRATION'
  expression_label: string
  min_value: string | null
  target_value: string | null
  max_value: string | null
  unit_label: string
  notes: string
}

export interface NutritionalReference extends ValidatedFields {
  id: number
  name: string
  species: number
  species_name: string
  breed: number | null
  breed_name: string | null
  category: number | null
  category_name: string | null
  physiological_stage: number | null
  physiological_stage_name: string | null
  objective: number | null
  objective_name: string | null
  system: number
  system_code: string
  age_min_months: string | null
  age_max_months: string | null
  weight_min_kg: string | null
  weight_max_kg: string | null
  dm_intake_min_kg_day: string | null
  dm_intake_max_kg_day: string | null
  application_conditions: string
  notes: string
  requirements: Requirement[]
}

export interface InclusionConstraint extends ValidatedFields {
  id: number
  species: number
  animal_category: number | null
  ingredient: number | null
  ingredient_category: number | null
  target_label: string
  min_pct_dm: string | null
  max_pct_dm: string | null
  rationale: string
}

export interface SourceDocument {
  id: number
  title: string
  authors: string
  publisher: string
  year: number | null
  source_type: string
  source_type_label: string
  identifier: string
  url: string
  notes: string
  is_demo: boolean
}
