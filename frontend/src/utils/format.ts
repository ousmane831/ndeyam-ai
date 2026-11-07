/** Formatage à la française (dates, nombres, montants). Une valeur absente s'affiche « — », jamais 0. */

const DATE = new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })
const DATE_TIME = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
const MONTH = new Intl.DateTimeFormat('fr-FR', { month: 'short', year: '2-digit' })

export const EMPTY = '—'

export function formatDate(value: string | null | undefined): string {
  if (!value) return EMPTY
  const date = value.length === 10 ? new Date(`${value}T00:00:00`) : new Date(value)
  return Number.isNaN(date.getTime()) ? EMPTY : DATE.format(date)
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return EMPTY
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? EMPTY : DATE_TIME.format(date)
}

export function formatMonth(value: string): string {
  return MONTH.format(new Date(`${value}-01T00:00:00`))
}

export function formatNumber(value: string | number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || value === '') return EMPTY
  const n = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(n)) return EMPTY
  return n.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: digits })
}

export function formatMoney(value: string | number | null | undefined, currency = 'XOF'): string {
  if (value === null || value === undefined || value === '') return EMPTY
  const n = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(n)) return EMPTY
  const label = currency === 'XOF' ? 'FCFA' : currency
  return `${n.toLocaleString('fr-FR', { maximumFractionDigits: 0 })} ${label}`
}

export function formatAge(days: number | null, estimated = false): string {
  if (days === null || days === undefined) return 'Âge inconnu'
  const prefix = estimated ? '≈ ' : ''
  if (days < 60) return `${prefix}${days} jours`
  const months = Math.floor(days / 30.44)
  if (months < 24) return `${prefix}${months} mois`
  const years = Math.floor(months / 12)
  const rest = months % 12
  return `${prefix}${years} an${years > 1 ? 's' : ''}${rest ? ` ${rest} mois` : ''}`
}

export function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
