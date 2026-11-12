import type { ValidationStatus } from './nutrition'

export interface Season {
  id: number
  code: string
  name: string
  start_month: number
  end_month: number
  months: number[]
  is_hot: boolean
  description: string
  sort_order: number
}

export type AvailabilityLevel = 'ABUNDANT' | 'AVAILABLE' | 'SCARCE' | 'UNAVAILABLE'

export interface IngredientAvailability {
  id: number
  farm: number
  ingredient: number
  ingredient_name: string
  season: number
  season_name: string
  level: AvailabilityLevel
  level_label: string
  notes: string
  is_demo: boolean
  created_at: string
}

export type AdviceTopic = 'WATER' | 'FEED' | 'SCHEDULE' | 'HOUSING' | 'OTHER'

export interface SeasonalAdvice {
  id: number
  season: number
  season_name: string
  species: number | null
  topic: AdviceTopic
  topic_label: string
  title: string
  text: string
  source: { id: number; title: string } | number | null
  reference_date: string | null
  is_demo: boolean
  status: ValidationStatus
  status_label: string
  validated_by_email: string | null
  validated_at: string | null
  validation_comment: string
  created_at: string
}

export interface CurrentSeason {
  date: string
  season: Season | null
  next_season: Season | null
  advice: SeasonalAdvice[]
  pending_advice: number
}
