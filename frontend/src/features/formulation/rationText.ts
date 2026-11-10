import type { Formula } from '@/types/formula'
import { formatDate, formatNumber } from '@/utils/format'

/** Nom d'aliment sans le préfixe « [DEMO] » (le statut DEMO est signalé à part). */
export const plainName = (name: string) => name.replace(/^\[DEMO\]\s*/, '')

/** Quantité lisible par un éleveur : grammes sous 1 kg (arrondis à 10 g), sinon kilos au dixième. */
export function practicalQuantity(kg: number): string {
  if (kg <= 0) return '0 kg'
  if (kg < 1) return `${Math.max(10, Math.round((kg * 1000) / 10 + 1e-9) * 10)} g`
  return `${formatNumber(Math.round(kg * 10 + 1e-9) / 10, 1)} kg`
}

type Verdict = { tone: 'ok' | 'wait' | 'stop'; text: string; share: string }

/** Ce que l'éleveur a le droit d'en faire, dit simplement (même règle que la création de ration). */
export function verdictOf(formula: Formula): Verdict {
  if (formula.is_demo) return { tone: 'stop', text: 'Données fictives de démonstration : ne pas utiliser pour nourrir des animaux.', share: 'DÉMONSTRATION : données fictives, ne pas utiliser.' }
  if (formula.status === 'VALIDATED') return { tone: 'ok', text: 'Vérifiée par un expert : vous pouvez la distribuer.', share: 'Ration vérifiée par un expert.' }
  if (formula.status === 'REJECTED') return { tone: 'stop', text: 'Rejetée par un expert : ne pas utiliser.', share: 'Ration REJETÉE par un expert : ne pas utiliser.' }
  if (formula.mode === 'MANUAL') return { tone: 'wait', text: 'Ration saisie : apports estimés, non vérifiés par un expert.', share: 'Ration saisie, non vérifiée par un expert.' }
  return { tone: 'wait', text: 'Estimation : à faire vérifier par un expert avant de nourrir les animaux.', share: 'ESTIMATION non vérifiée par un expert : ne pas utiliser avant vérification.' }
}

/** Nom par défaut d'une formule rapide : « Ration <lot> — jj/mm/aaaa ». */
export const quickFormulaName = (group: string) => `Ration ${group} — ${formatDate(new Date().toISOString())}`
