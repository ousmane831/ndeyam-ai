import { tk } from '@/i18n'

/** Validation de la saisie d'une distribution (miroir des règles de l'API). */
export interface FeedingFormValues {
  distributed: string
  consumed: string
  refused: string
  targetIsGroup: boolean
  heads: string
  date: string
}

const n = (v: string) => Number(v.replace(',', '.'))

export function validateFeeding(v: FeedingFormValues, today: string): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!v.date) errors.date = tk('Date obligatoire.')
  else if (v.date > today) errors.date = tk('La date ne peut pas être dans le futur.')
  if (!v.distributed.trim() || Number.isNaN(n(v.distributed)) || n(v.distributed) < 0) errors.distributed = tk('Quantité distribuée (kg brut) obligatoire.')
  for (const [key, invalid] of [['consumed', tk('Quantité consommée invalide.')], ['refused', tk('Quantité refusée invalide.')]] as const) {
    const value = v[key].trim()
    if (!value) continue
    if (Number.isNaN(n(value)) || n(value) < 0) errors[key] = invalid
    else if (!errors.distributed && n(value) > n(v.distributed)) errors[key] = tk('Ne peut pas dépasser la quantité distribuée.')
  }
  if (v.targetIsGroup && !(Number.isInteger(n(v.heads)) && n(v.heads) > 0)) errors.heads = tk("Nombre d'animaux nourris obligatoire pour un lot.")
  return errors
}
