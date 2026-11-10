/**
 * Formatage selon la langue de l'interface (dates, nombres, montants) : fr-FR ou en-GB (jour/mois/année dans les
 * deux cas). Une valeur absente s'affiche « — », jamais 0.
 */
import { currentLocale, t } from '@/i18n'

const formats = new Map<string, { date: Intl.DateTimeFormat; dateTime: Intl.DateTimeFormat; month: Intl.DateTimeFormat }>()
function fmt() {
  const locale = currentLocale()
  let f = formats.get(locale)
  if (!f) {
    f = {
      date: new Intl.DateTimeFormat(locale, { day: '2-digit', month: '2-digit', year: 'numeric' }),
      dateTime: new Intl.DateTimeFormat(locale, { dateStyle: 'short', timeStyle: 'short' }),
      month: new Intl.DateTimeFormat(locale, { month: 'short', year: '2-digit' }),
    }
    formats.set(locale, f)
  }
  return f
}

export const EMPTY = '—'

export function formatDate(value: string | null | undefined): string {
  if (!value) return EMPTY
  const date = value.length === 10 ? new Date(`${value}T00:00:00`) : new Date(value)
  return Number.isNaN(date.getTime()) ? EMPTY : fmt().date.format(date)
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return EMPTY
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? EMPTY : fmt().dateTime.format(date)
}

export function formatMonth(value: string): string {
  return fmt().month.format(new Date(`${value}-01T00:00:00`))
}

export function formatNumber(value: string | number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || value === '') return EMPTY
  const n = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(n)) return EMPTY
  return n.toLocaleString(currentLocale(), { minimumFractionDigits: 0, maximumFractionDigits: digits })
}

export function formatMoney(value: string | number | null | undefined, currency = 'XOF'): string {
  if (value === null || value === undefined || value === '') return EMPTY
  const n = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(n)) return EMPTY
  const label = currency === 'XOF' ? 'FCFA' : currency
  return `${n.toLocaleString(currentLocale(), { maximumFractionDigits: 0 })} ${label}`
}

export function formatAge(days: number | null, estimated = false): string {
  if (days === null || days === undefined) return t('Âge inconnu')
  const prefix = estimated ? '≈ ' : ''
  if (days < 60) return prefix + t('{{count}} jours', { count: days })
  const months = Math.floor(days / 30.44)
  if (months < 24) return prefix + t('{{count}} mois', { count: months })
  const years = Math.floor(months / 12)
  const rest = months % 12
  const y = years > 1 ? t('{{count}} ans', { count: years }) : t('1 an')
  return prefix + y + (rest ? ` ${t('{{count}} mois', { count: rest })}` : '')
}

export function todayIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
