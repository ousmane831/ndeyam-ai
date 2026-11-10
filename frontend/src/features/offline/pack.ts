import { api } from '@/services/api'
import type { PackProblem } from './engine'
import { readJson, writeJson } from './storage'

/** Paquet de calcul hors ligne d'une exploitation (`GET /formulas/offline-pack/?farm=`). */
export interface PackReference {
  id: number
  name: string
  species: number
  criteria: {
    breed: number | null
    category: number | null
    physiological_stage: number | null
    objective: number | null
    weight_min_kg: number | null
    weight_max_kg: number | null
    age_min_months: number | null
    age_max_months: number | null
  }
  problem: PackProblem
  warnings: string[]
}
export interface PackGroup {
  id: number
  name: string
  head_count: number
  profile_notes: string[]
  species: number | null
  breed: number | null
  category: number | null
  physiological_stage: number | null
  weight_kg: number | null
  age_months: number | null
}
export interface OfflinePack {
  farm: number
  is_demo: boolean
  generated_at: string
  engine_version: string
  ingredients: { id: number; name: string; category_code: string; local_names: string }[]
  references: PackReference[]
  groups: PackGroup[]
  objectives: { id: number; name: string }[]
  animals: { id: number; tag_number: string; name: string; group: number | null; last_weight: { weight_kg: string; weighed_on: string } | null }[]
}

const key = (farm: number) => `ndeyam.pack.${farm}`

export async function downloadPack(farm: number): Promise<OfflinePack> {
  const pack = (await api.get<OfflinePack>('/formulas/offline-pack/', { params: { farm } })).data
  writeJson(key(farm), pack)
  return pack
}

export const loadPack = (farm: number) => readJson<OfflinePack | null>(key(farm), null)
