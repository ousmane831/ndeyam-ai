import { createContext } from 'react'
import type { Farm } from '@/types/farm'

export interface FarmContextValue {
  farms: Farm[]
  isLoading: boolean
  /** Exploitation consultée (null = toutes les exploitations accessibles). */
  selectedFarmId: number | null
  selectFarm: (id: number | null) => void
  /** Exploitations où l'utilisateur peut écrire (propriétaire, gestionnaire ou administrateur). */
  writableFarms: Farm[]
  /** Exploitation proposée par défaut dans les formulaires de création. */
  defaultWritableFarmId: number | null
  canWrite: (farmId: number) => boolean
  /** Pesées : propriétaire, gestionnaire, technicien d'élevage (ou administrateur). */
  canWeigh: (farmId: number) => boolean
  /** Observations (santé…) : propriétaire, gestionnaire, technicien, vétérinaire (ou administrateur). */
  canObserve: (farmId: number) => boolean
  /** Validation des rations : nutritionniste / zootechnicien invité (ou administrateur). */
  canReviewRations: (farmId: number) => boolean
}

export const FarmContext = createContext<FarmContextValue | null>(null)
