import { tk } from '@/i18n'

/** Méthodes de pesée proposées dans les formulaires. */
export const METHOD_OPTIONS = [
  { value: 'SCALE', label: tk('Balance / bascule') },
  { value: 'TAPE', label: tk('Ruban barymétrique') },
  { value: 'VISUAL', label: tk('Estimation visuelle') },
]
