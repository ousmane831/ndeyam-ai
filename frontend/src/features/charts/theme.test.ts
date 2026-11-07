import { describe, expect, it } from 'vitest'
import { niceTicks } from './theme'

describe('niceTicks', () => {
  it('produit des graduations régulières qui encadrent les valeurs', () => {
    const ticks = niceTicks([30, 33, 34.5])
    const steps = new Set(ticks.slice(1).map((t, i) => t - ticks[i]))
    expect(steps.size).toBe(1)
    expect(ticks[0]).toBeLessThanOrEqual(30)
    expect(ticks[ticks.length - 1]).toBeGreaterThanOrEqual(34.5)
    expect(ticks.length).toBeGreaterThanOrEqual(3)
    expect(ticks.length).toBeLessThanOrEqual(7)
  })

  it('gère une seule valeur et une liste vide', () => {
    expect(niceTicks([42]).length).toBeGreaterThanOrEqual(2)
    expect(niceTicks([])).toEqual([])
  })
})
