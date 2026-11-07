import { describe, expect, it } from 'vitest'
import { validateFeeding } from './feedingForm'

const ok = { distributed: '2,5', consumed: '', refused: '', targetIsGroup: false, heads: '', date: '2026-11-01' }

describe('validateFeeding', () => {
  it('accepte une distribution sans consommation mesurée (jamais supposée)', () => {
    expect(validateFeeding(ok, '2026-11-07')).toEqual({})
  })

  it('refuse une consommation ou des refus supérieurs à la quantité distribuée', () => {
    const errors = validateFeeding({ ...ok, consumed: '3', refused: '2,6' }, '2026-11-07')
    expect(errors.consumed).toMatch(/dépasser/)
    expect(errors.refused).toMatch(/dépasser/)
  })

  it('exige la quantité distribuée, une date passée et l’effectif pour un lot', () => {
    const errors = validateFeeding({ ...ok, distributed: '', date: '2026-12-01', targetIsGroup: true }, '2026-11-07')
    expect(Object.keys(errors).sort()).toEqual(['date', 'distributed', 'heads'])
  })
})
