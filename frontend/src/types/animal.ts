export type Sex = 'M' | 'F'
export type AnimalStatus = 'ACTIVE' | 'SOLD' | 'DEAD' | 'ARCHIVED'
export type WeighingMethod = 'SCALE' | 'TAPE' | 'VISUAL'

export interface Species {
  id: number
  code: string
  name: string
  scientific_name: string
  is_active: boolean
}

export interface NamedRef {
  id: number
  species?: number
  code?: string
  name: string
}

export interface Animal {
  id: number
  uuid: string
  farm: number
  tag_number: string
  name: string
  species: number
  species_name: string
  breed: number | null
  breed_name: string | null
  sex: Sex
  sex_label: string
  birth_date: string | null
  birth_date_is_estimated: boolean
  age_days: number | null
  initial_weight_kg: string | null
  last_weight: { weight_kg: string; weighed_on: string; unit: string } | null
  category: number | null
  category_name: string | null
  physiological_stage: number | null
  physiological_stage_name: string | null
  group: number | null
  group_name: string | null
  registered_on: string
  observations: string
  status: AnimalStatus
  status_label: string
  archived_at: string | null
  is_demo: boolean
  created_at: string
  updated_at: string
}

export interface AnimalPayload {
  farm: number
  tag_number: string
  name?: string
  species: number
  breed?: number | null
  sex: Sex
  birth_date?: string | null
  estimated_age_months?: string | null
  initial_weight_kg?: string | null
  category?: number | null
  physiological_stage?: number | null
  group?: number | null
  registered_on?: string
  observations?: string
}

export interface AnimalGroup {
  id: number
  farm: number
  name: string
  species: number | null
  species_name: string | null
  description: string
  is_active: boolean
  is_demo: boolean
  animals_count: number
}

export interface Observation {
  id: number
  observed_on: string
  kind: string
  kind_label: string
  text: string
  author_email: string | null
  created_at: string
}

export interface HistoryEvent {
  type: 'weighing' | 'observation' | 'ration' | 'feeding' | 'registration'
  date: string
  label: string
  details: Record<string, unknown>
}

export interface Weighing {
  id: number
  animal: number
  animal_tag: string
  weighed_on: string
  weight_kg: string
  unit: string
  method: WeighingMethod
  method_label: string
  observations: string
  is_demo: boolean
  recorded_by_email: string | null
}

export interface GrowthInterval {
  from: string
  to: string
  days: number
  weight_change_kg: string
  adg_g_per_day: string | null
  low_reliability: boolean
}

export interface AnimalGrowth {
  animal_id: number
  tag_number: string
  points: { date: string; weight_kg: string; method: string; origin: 'weighing' | 'initial' }[]
  intervals: GrowthInterval[]
  overall: GrowthInterval | null
  latest_interval: GrowthInterval | null
  unavailable_reason: string | null
  formula: string
  monitoring_range: { id: number; name: string; adg_min_g: string | null; adg_max_g: string | null; source: string } | null
  latest_vs_range: 'below' | 'within' | 'above' | null
  monitoring_note: string
}

export interface GroupGrowth {
  group_id: number
  group_name: string
  animals: {
    animal_id: number
    tag_number: string
    name: string
    last_weight_kg: string | null
    last_weighed_on: string | null
    adg_g_per_day: string | null
    measurements: number
  }[]
  animals_count: number
  animals_with_adg: number
  mean_adg_g_per_day: string | null
  note: string
}

export interface ImportBatch {
  id: number
  kind: string
  file_name: string
  status: string
  status_label: string
  total_rows: number
  created_rows: number
  updated_rows: number
  error_rows: number
  errors: { line: number | null; error: string }[]
}
