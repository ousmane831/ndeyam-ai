import { describe, expect, it } from 'vitest'
import { EMPTY, formatAge, formatDate, formatMoney, formatNumber } from './format'

describe('formatage', () => {
  it('affiche « — » pour une valeur absente, jamais zéro', () => {
    expect(formatNumber(null)).toBe(EMPTY)
    expect(formatMoney(undefined)).toBe(EMPTY)
    expect(formatDate(null)).toBe(EMPTY)
  })

  it('formate à la française', () => {
    expect(formatDate('2026-11-07')).toBe('07/11/2026')
    expect(formatNumber('28.50', 2)).toBe('28,5')
    expect(formatMoney('12500.4')).toMatch(/^12\s?500 FCFA$/)
  })

  it("exprime l'âge en jours, mois ou années et signale l'estimation", () => {
    expect(formatAge(null)).toBe('Âge inconnu')
    expect(formatAge(45)).toBe('45 jours')
    expect(formatAge(200, true)).toBe('≈ 6 mois')
    expect(formatAge(800)).toBe('2 ans 2 mois')
  })
})
