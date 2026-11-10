import { describe, expect, it } from 'vitest'
import rawCases from './engine-cases.fixture.json'
import { formulateOffline, restrictProblem, type PackProblem } from './engine'

type Case = {
  name: string
  problem: PackProblem
  expected: { status: string; dm_intake_kg_day: number | null; cost_per_day: number | null; items: Record<string, number>; excluded: number[]; constraints_ok: boolean | null }
}

/** Objectif du mode équilibré (écarts relatifs aux cibles), pour comparer deux solutions optimales. */
function balancedScore(problem: PackProblem, q: Record<string, number>) {
  const total = Object.values(q).reduce((s, v) => s + v, 0)
  let score = 0
  for (const r of problem.requirements) {
    const target = r.target_value ?? (r.min_value !== null && r.max_value !== null ? (r.min_value + r.max_value) / 2 : null)
    if (target === null || target <= 0) continue
    const supply = problem.ingredients.reduce((s, i) => s + (q[String(i.id)] ?? 0) * (i.composition_per_kg_dm[String(r.nutrient_id)] ?? 0), 0)
    const ref = r.expression === 'DAILY_AMOUNT' ? target : target * total
    score += Math.abs(supply - ref) / target
  }
  return score
}

const cases = rawCases as unknown as Case[]

const close = (a: number | null, b: number | null, rel = 1e-4) =>
  a === null || b === null ? a === b : Math.abs(a - b) <= rel * Math.max(1, Math.abs(b))

describe('moteur hors ligne : parité avec le moteur Python (PuLP / CBC)', () => {
  it.each(cases.map((c) => [c.name, c] as const))('%s', (_name, c) => {
    const result = formulateOffline(c.problem)
    expect(result.status).toBe(c.expected.status)
    expect(result.excluded.map((e) => e.ingredient_id).sort((a, b) => a - b)).toEqual(c.expected.excluded)
    if (c.expected.status !== 'ESTIMATED') return
    expect(result.checks.every((x) => x.status === 'ok')).toBe(c.expected.constraints_ok)
    const mine = Object.fromEntries(result.items.map((i) => [String(i.ingredient_id), i.quantity_dm_kg]))
    if (c.problem.mode === 'ECONOMIC') {
      // Coût minimal : unique, même si plusieurs rations l'atteignent.
      expect(close(result.cost_per_day, c.expected.cost_per_day)).toBe(true)
      expect(close(result.dm_intake_kg_day, c.expected.dm_intake_kg_day)).toBe(true)
    } else {
      // Équilibré : écart aux cibles aussi bon que celui du moteur Python.
      expect(balancedScore(c.problem, mine)).toBeLessThanOrEqual(balancedScore(c.problem, c.expected.items) + 1e-4)
    }
  })

  it('restreint un problème aux ingrédients choisis, plafonds compris', () => {
    const c = cases.find((x) => x.name === 'economique_teneur_et_plafond')!
    const p = restrictProblem(c.problem, [1, 2], 'BALANCED')
    expect(p.mode).toBe('BALANCED')
    expect(p.ingredients.map((i) => i.id)).toEqual([1, 2])
    expect(p.inclusion_bounds).toEqual([]) // les plafonds de C et D ne concernent plus aucun ingrédient
  })

  it('refuse avec les mêmes motifs que le serveur, sans rien supposer', () => {
    const c = cases.find((x) => x.name === 'refus_sans_besoin')!
    expect(formulateOffline(c.problem).refusal_reasons).toEqual(["Aucun besoin nutritionnel validé n'est disponible pour ce profil d'animal."])
  })
})
