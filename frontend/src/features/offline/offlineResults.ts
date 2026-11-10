import { useSyncExternalStore } from 'react'
import type { OfflineResult } from './engine'
import { readJson, writeJson } from './storage'

/** Calculs faits hors ligne, gardés sur l'appareil jusqu'au recalcul officiel par le serveur. */
export interface OfflineFormula {
  id: string
  name: string
  farm: number
  isDemo: boolean
  createdAt: string
  referenceName: string
  headCount: number
  notes: string[]
  /** Code de catégorie de chaque ingrédient (pictogrammes). */
  categories?: Record<number, string>
  result: OfflineResult
  /** Formule officielle enregistrée par le serveur après synchronisation. */
  serverFormulaId?: number
}

const KEY = 'ndeyam.offline-results'
const listeners = new Set<() => void>()
let cache: OfflineFormula[] | null = null
const all = (): OfflineFormula[] => (cache ??= readJson<OfflineFormula[]>(KEY, []))
const save = (list: OfflineFormula[]) => {
  cache = list.slice(-20) // les 20 derniers suffisent
  writeJson(KEY, cache)
  listeners.forEach((l) => l())
}

export function saveOfflineFormula(f: OfflineFormula) {
  save([...all().filter((x) => x.id !== f.id), f])
}

export function linkOfflineResult(id: string, serverFormulaId: number) {
  save(all().map((x) => (x.id === id ? { ...x, serverFormulaId } : x)))
}

export function resetOfflineResultsCache() {
  cache = null
  listeners.forEach((l) => l())
}

export function useOfflineFormula(id: string | undefined): OfflineFormula | undefined {
  const list = useSyncExternalStore((cb) => { listeners.add(cb); return () => listeners.delete(cb) }, all, all)
  return list.find((x) => x.id === id)
}
