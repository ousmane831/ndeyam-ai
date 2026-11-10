import { t } from '@/i18n'
import type { Formula } from '@/types/formula'

type RationCandidate = Pick<Formula, 'mode' | 'status' | 'is_demo'>

/**
 * Raison pour laquelle une formule ne peut pas devenir une ration (null si elle le peut).
 * Miroir de `feeding.serializers.ration_blocker` : le serveur reste juge, l'interface évite seulement
 * de proposer une action qui serait refusée.
 */
export function rationBlocker(f: RationCandidate): string | null {
  if (f.is_demo) return null
  if (f.mode === 'MANUAL') return f.status === 'REJECTED' ? t('Cette formule a été rejetée par un expert.') : null
  if (f.status === 'VALIDATED') return null
  if (f.status === 'PENDING_REVIEW') return t('En attente de l’avis d’un expert : vous pourrez créer une ration dès sa validation.')
  if (f.status === 'ESTIMATED') return t('Une estimation doit être validée par un expert avant de devenir une ration.')
  return t('Cette formule ne peut pas devenir une ration.')
}

export const canCreateRation = (f: RationCandidate) => rationBlocker(f) === null
