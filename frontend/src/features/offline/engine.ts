/**
 * Moteur de formulation HORS LIGNE : portage fidèle du moteur Python (formulations/engine) pour estimer une
 * ration sans connexion, à partir du paquet préparé par le serveur (`/formulas/offline-pack/`).
 *
 * Mêmes règles : refus motivés, exclusions d'ingrédients (MS inconnue, nutriment soumis à contrainte inconnu,
 * prix manquant en mode économique), programme linéaire identique (économique : coût minimal ; équilibré :
 * écarts aux cibles + coût en second critère), recalcul indépendant des contraintes.
 * Différence assumée : en cas d'impossibilité, pas de diagnostic détaillé (le serveur le donnera).
 * Le résultat reste PROVISOIRE : la formule officielle est recalculée par le serveur à la reconnexion.
 * Parité vérifiée sur les cas de référence calculés par le moteur Python (engine-cases.fixture.json).
 */
import solver from 'javascript-lp-solver'

export type Mode = 'ECONOMIC' | 'BALANCED'
type Expression = 'DAILY_AMOUNT' | 'DIET_CONCENTRATION'

export interface PackNutrient { id: number; code: string; name: string; amount_unit: string; system: string | null }
export interface PackRequirement { nutrient_id: number; expression: Expression; min_value: number | null; target_value: number | null; max_value: number | null }
export interface PackIngredient {
  id: number
  name: string
  dm_g_per_kg_as_fed: number | null
  composition_per_kg_dm: Record<string, number>
  price_per_kg_as_fed: number | null
  currency: string
  price_is_demo: boolean
  max_as_fed_kg_per_day?: number | null
}
export interface PackBound { label: string; ingredient_ids: number[]; min_pct_dm: number | null; max_pct_dm: number | null }
export interface PackProblem {
  mode: Mode
  nutrients: Record<string, PackNutrient>
  requirements: PackRequirement[]
  ingredients: PackIngredient[]
  dm_intake_min_kg: number | null
  dm_intake_max_kg: number | null
  inclusion_bounds: PackBound[]
  reference_label: string
  reference_source: string
  is_demo: boolean
}

export interface OfflineItem {
  ingredient_id: number
  name: string
  inclusion_pct_dm: number
  quantity_dm_kg: number
  quantity_as_fed_kg: number
  price_per_kg_as_fed: number | null
  cost_per_day: number | null
}
export interface RequirementCheck { code: string; label: string; value: number | null; min: number | null; max: number | null; unit: string; status: 'ok' | 'below' | 'above' | 'unknown' }
export interface OfflineResult {
  status: 'ESTIMATED' | 'INFEASIBLE' | 'REFUSED'
  mode: Mode
  items: OfflineItem[]
  dm_intake_kg_day: number | null
  as_fed_kg_day: number | null
  cost_per_day: number | null
  cost_per_kg_as_fed: number | null
  currency: string
  checks: RequirementCheck[]
  refusal_reasons: string[]
  warnings: string[]
  excluded: { ingredient_id: number; name: string; reasons: string[] }[]
}

const REL_TOLERANCE = 1e-4
const dmFraction = (i: PackIngredient) => (i.dm_g_per_kg_as_fed ? i.dm_g_per_kg_as_fed / 1000 : null)
const pricePerKgDm = (i: PackIngredient) => {
  const f = dmFraction(i)
  return i.price_per_kg_as_fed === null || !f ? null : i.price_per_kg_as_fed / f
}
const comp = (i: PackIngredient, n: number) => i.composition_per_kg_dm[String(n)]

function within(value: number, low: number | null, high: number | null): 'ok' | 'below' | 'above' {
  if (low !== null && value < low - REL_TOLERANCE * Math.max(1, Math.abs(low))) return 'below'
  if (high !== null && value > high + REL_TOLERANCE * Math.max(1, Math.abs(high))) return 'above'
  return 'ok'
}

function empty(problem: PackProblem, status: OfflineResult['status']): OfflineResult {
  return { status, mode: problem.mode, items: [], dm_intake_kg_day: null, as_fed_kg_day: null, cost_per_day: null, cost_per_kg_as_fed: null,
    currency: problem.ingredients[0]?.currency ?? 'XOF', checks: [], refusal_reasons: [], warnings: [], excluded: [] }
}

/** Contrôles préalables (checks.py) : refus motivés et exclusions, jamais de valeur supposée. */
function prepare(problem: PackProblem) {
  const reasons: string[] = []
  const warnings: string[] = []
  const excluded: OfflineResult['excluded'] = []
  if (problem.requirements.length === 0) reasons.push("Aucun besoin nutritionnel validé n'est disponible pour ce profil d'animal.")
  if (problem.dm_intake_min_kg === null && problem.dm_intake_max_kg === null) {
    reasons.push("L'ingestion de matière sèche (kg MS/jour) n'est pas renseignée dans la référence nutritionnelle : impossible de dimensionner la ration.")
  }
  if (problem.ingredients.length === 0) reasons.push("Aucun ingrédient n'a été proposé.")
  const constrained = [...new Set(problem.requirements.map((r) => r.nutrient_id))].sort((a, b) => a - b)
  const kept: PackIngredient[] = []
  for (const ing of problem.ingredients) {
    const why: string[] = []
    if (!dmFraction(ing)) why.push('teneur en matière sèche inconnue')
    const missing = constrained.filter((n) => comp(ing, n) === undefined).map((n) => problem.nutrients[String(n)].code)
    if (missing.length) why.push(`valeur(s) validée(s) inconnue(s) pour : ${missing.join(', ')}`)
    if (problem.mode === 'ECONOMIC' && ing.price_per_kg_as_fed === null) why.push('prix inconnu (indispensable en mode économique)')
    if (ing.max_as_fed_kg_per_day != null && ing.max_as_fed_kg_per_day <= 0) why.push('quantité disponible nulle')
    if (why.length) {
      excluded.push({ ingredient_id: ing.id, name: ing.name, reasons: why })
      warnings.push(`« ${ing.name} » exclu : ${why.join(' ; ')}.`)
    } else {
      kept.push(ing)
      if (ing.price_is_demo) warnings.push(`Le prix de « ${ing.name} » est une donnée DEMO.`)
    }
  }
  if (problem.ingredients.length && !kept.length) reasons.push('Aucun ingrédient proposé ne dispose de toutes les données validées nécessaires.')
  let useCost = true
  if (kept.length && kept.some((i) => i.price_per_kg_as_fed === null)) {
    useCost = false
    warnings.push("Certains prix sont inconnus : le coût n'est pas pris en compte ni calculé.")
  }
  return { kept, reasons, warnings, excluded, useCost }
}

type Model = { optimize: string; opType: 'min'; constraints: Record<string, { min?: number; max?: number; equal?: number }>; variables: Record<string, Record<string, number>> }
const OBJ = '__objectif'

/** Contraintes du programme linéaire (solver.py, _constraint_rows) : x_i = kg de MS de l'ingrédient i par animal et par jour. */
function buildModel(problem: PackProblem, kept: PackIngredient[], useCost: boolean): Model {
  const model: Model = { optimize: OBJ, opType: 'min', constraints: {}, variables: {} }
  const v = (id: number | string) => (model.variables[`x_${id}`] ??= {})
  for (const i of kept) v(i.id)[OBJ] = 0
  const set = (name: string, bound: { min?: number; max?: number; equal?: number }, coef: (i: PackIngredient) => number) => {
    model.constraints[name] = bound
    for (const i of kept) v(i.id)[name] = coef(i)
  }
  if (problem.dm_intake_min_kg !== null || problem.dm_intake_max_kg !== null) {
    set('intake', { ...(problem.dm_intake_min_kg !== null && { min: problem.dm_intake_min_kg }), ...(problem.dm_intake_max_kg !== null && { max: problem.dm_intake_max_kg }) }, () => 1)
  }
  for (const r of problem.requirements) {
    const n = r.nutrient_id
    if (r.expression === 'DAILY_AMOUNT') {
      set(`req_${n}_daily`, { ...(r.min_value !== null && { min: r.min_value }), ...(r.max_value !== null && { max: r.max_value }) }, (i) => comp(i, n))
    } else {
      // Teneur : min · Σx ≤ Σ c·x ≤ max · Σx, linéarisée en Σ (c − borne)·x.
      if (r.min_value !== null) set(`req_${n}_conc_min`, { min: 0 }, (i) => comp(i, n) - r.min_value!)
      if (r.max_value !== null) set(`req_${n}_conc_max`, { max: 0 }, (i) => comp(i, n) - r.max_value!)
    }
  }
  problem.inclusion_bounds.forEach((b, k) => {
    const inSet = (i: PackIngredient) => (b.ingredient_ids.includes(i.id) ? 1 : 0)
    if (b.min_pct_dm !== null) set(`incl_${k}_min`, { min: 0 }, (i) => inSet(i) - b.min_pct_dm! / 100)
    if (b.max_pct_dm !== null) set(`incl_${k}_max`, { max: 0 }, (i) => inSet(i) - b.max_pct_dm! / 100)
  })
  for (const i of kept) {
    if (i.max_as_fed_kg_per_day != null) {
      model.constraints[`avail_${i.id}`] = { max: i.max_as_fed_kg_per_day * dmFraction(i)! }
      v(i.id)[`avail_${i.id}`] = 1
    }
  }

  if (problem.mode === 'ECONOMIC') {
    for (const i of kept) v(i.id)[OBJ] = useCost ? pricePerKgDm(i)! : 0
    return model
  }
  // Équilibré : Σ |apport − cible| / cible, la cible étant la valeur « cible » ou le milieu de [min, max].
  for (const r of problem.requirements) {
    let target = r.target_value
    if (target === null && r.min_value !== null && r.max_value !== null) target = (r.min_value + r.max_value) / 2
    if (target === null || target <= 0) continue
    const name = `target_${r.nutrient_id}_${r.expression}`
    const daily = r.expression === 'DAILY_AMOUNT'
    model.constraints[name] = { equal: daily ? target : 0 }
    for (const i of kept) v(i.id)[name] = daily ? comp(i, r.nutrient_id) : comp(i, r.nutrient_id) - target
    v(`pos_${name}`)[name] = -1
    v(`pos_${name}`)[OBJ] = 1 / target
    v(`neg_${name}`)[name] = 1
    v(`neg_${name}`)[OBJ] = 1 / target
  }
  if (useCost) {
    const maxPrice = Math.max(...kept.map((i) => pricePerKgDm(i)!)) || 1
    for (const i of kept) v(i.id)[OBJ] += pricePerKgDm(i)! * (1e-3 / maxPrice)
  }
  return model
}

/** Résultat et recalcul indépendant (verify.py) : une ration n'est conforme que si chaque contrainte l'est. */
function buildResult(problem: PackProblem, kept: PackIngredient[], useCost: boolean, quantities: Map<number, number>, base: OfflineResult): OfflineResult {
  const byId = new Map(kept.map((i) => [i.id, i]))
  const totalDm = [...quantities.values()].reduce((s, q) => s + q, 0)
  const used = [...quantities.entries()].filter(([, q]) => q > 1e-9)
  const totalAsFed = used.reduce((s, [id, q]) => s + q / dmFraction(byId.get(id)!)!, 0)
  let totalCost = 0
  const items: OfflineItem[] = used.sort((a, b) => b[1] - a[1]).map(([id, qDm]) => {
    const ing = byId.get(id)!
    const qAf = qDm / dmFraction(ing)!
    const cost = useCost ? qAf * ing.price_per_kg_as_fed! : null
    totalCost += cost ?? 0
    return { ingredient_id: id, name: ing.name, inclusion_pct_dm: totalDm ? (100 * qDm) / totalDm : 0, quantity_dm_kg: qDm, quantity_as_fed_kg: qAf, price_per_kg_as_fed: ing.price_per_kg_as_fed, cost_per_day: cost }
  })
  const checks: RequirementCheck[] = []
  if (problem.dm_intake_min_kg !== null || problem.dm_intake_max_kg !== null) {
    checks.push({ code: 'MS', label: 'Ingestion de matière sèche', value: totalDm, min: problem.dm_intake_min_kg, max: problem.dm_intake_max_kg, unit: 'kg MS/jour',
      status: within(totalDm, problem.dm_intake_min_kg, problem.dm_intake_max_kg) })
  }
  for (const r of problem.requirements) {
    const n = problem.nutrients[String(r.nutrient_id)]
    const missing = used.some(([id]) => comp(byId.get(id)!, r.nutrient_id) === undefined)
    const daily = missing ? null : used.reduce((s, [id, q]) => s + q * comp(byId.get(id)!, r.nutrient_id), 0)
    const isDaily = r.expression === 'DAILY_AMOUNT'
    const value = daily === null ? null : isDaily ? daily : totalDm ? daily / totalDm : null
    checks.push({ code: n.code, label: `${n.code} (${isDaily ? 'apport journalier' : 'teneur'})`, value, min: r.min_value, max: r.max_value,
      unit: isDaily ? `${n.amount_unit}/jour` : `${n.amount_unit}/kg MS`, status: value === null ? 'unknown' : within(value, r.min_value, r.max_value) })
  }
  for (const b of problem.inclusion_bounds) {
    const share = totalDm ? (100 * b.ingredient_ids.reduce((s, id) => s + (quantities.get(id) ?? 0), 0)) / totalDm : 0
    checks.push({ code: 'INCL', label: `Incorporation : ${b.label}`, value: share, min: b.min_pct_dm, max: b.max_pct_dm, unit: '% MS', status: within(share, b.min_pct_dm, b.max_pct_dm) })
  }
  for (const i of kept) {
    if (i.max_as_fed_kg_per_day != null) {
      const qAf = (quantities.get(i.id) ?? 0) / dmFraction(i)!
      checks.push({ code: 'DISPO', label: `Disponibilité : ${i.name}`, value: qAf, min: null, max: i.max_as_fed_kg_per_day, unit: 'kg brut/jour', status: within(qAf, null, i.max_as_fed_kg_per_day) })
    }
  }
  const allOk = checks.every((c) => c.status === 'ok')
  const warnings = [...base.warnings]
  if (!allOk) warnings.push("Le recalcul indépendant révèle une contrainte non respectée : la ration n'est pas conforme.")
  return {
    ...base,
    status: allOk ? 'ESTIMATED' : 'INFEASIBLE',
    items,
    dm_intake_kg_day: totalDm,
    as_fed_kg_day: totalAsFed,
    cost_per_day: useCost ? totalCost : null,
    cost_per_kg_as_fed: useCost && totalAsFed ? totalCost / totalAsFed : null,
    checks,
    warnings,
  }
}

export function formulateOffline(problem: PackProblem): OfflineResult {
  const prepared = prepare(problem)
  const base = { ...empty(problem, 'REFUSED'), warnings: prepared.warnings, excluded: prepared.excluded }
  if (prepared.reasons.length) return { ...base, refusal_reasons: prepared.reasons }
  const model = buildModel(problem, prepared.kept, prepared.useCost)
  const solution = solver.Solve(model as never) as Record<string, number | boolean | undefined>
  if (!solution.feasible) {
    return {
      ...base,
      status: 'INFEASIBLE',
      refusal_reasons: [
        'Aucune ration ne permet de respecter simultanément toutes les contraintes avec les ingrédients proposés. '
        + 'Ajoutez des ingrédients ou faites revoir les contraintes par un expert. Le diagnostic détaillé sera donné par le serveur à la reconnexion.',
      ],
    }
  }
  const quantities = new Map(prepared.kept.map((i) => [i.id, Math.max(Number(solution[`x_${i.id}`] ?? 0), 0)]))
  return buildResult(problem, prepared.kept, prepared.useCost, quantities, base)
}

/** Restreint un problème du paquet aux ingrédients choisis (les plafonds d'incorporation suivent). */
export function restrictProblem(problem: PackProblem, ingredientIds: number[], mode: Mode): PackProblem {
  const ids = new Set(ingredientIds)
  return {
    ...problem,
    mode,
    ingredients: problem.ingredients.filter((i) => ids.has(i.id)),
    inclusion_bounds: problem.inclusion_bounds
      .map((b) => ({ ...b, ingredient_ids: b.ingredient_ids.filter((i) => ids.has(i)) }))
      .filter((b) => b.ingredient_ids.length > 0),
  }
}
