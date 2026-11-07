export interface DashboardData {
  farms_count: number
  animals: {
    total: number
    by_species: { code: string; name: string; count: number }[]
    by_category: { name: string; count: number }[]
    by_sex: { M: number; F: number }
  }
  groups_count: number
  weighings: {
    last_30_days: number
    never_weighed: number
    latest: { id: number; animal_id: number; animal: string; weighed_on: string; weight_kg: string }[]
  }
  weight_trend: { points: { month: string; mean_weight_kg: number; weighings: number; animals: number }[]; note: string }
  rations: {
    active_count: number
    active: { id: number; name: string; formula: string; formula_status: string; target: string; start_date: string }[]
  }
  feeding_cost: {
    period_days: number
    estimated_cost: string | null
    distributed_kg: string | null
    records: number
    records_without_cost: number
    currency: string
  }
  alerts: {
    open: number
    by_severity: Partial<Record<'INFO' | 'WARNING' | 'CRITICAL', number>>
    latest: { id: number; title: string; severity: string; alert_type: string }[]
  }
  recent_activity: { id: number; action: string; label: string; object: string; actor: string | null; created_at: string }[]
}
