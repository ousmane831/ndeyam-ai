import { t } from '@/i18n'
import { formulateOffline, restrictProblem, type Mode, type OfflineResult } from './engine'
import type { OfflinePack, PackGroup, PackReference } from './pack'

type Profile = { species: number | null; breed: number | null; category: number | null; physiological_stage: number | null; objective: number | null; weight_kg: number | null; age_months: number | null }

/** Même choix que le serveur (engine_service.match_reference) : la référence applicable la plus spécifique. */
export function matchReference(references: PackReference[], p: Profile): PackReference | null {
  const fits = (value: number | null, ref: number | null) => (value ? ref === null || ref === value : ref === null)
  const inRange = (value: number | null, min: number | null, max: number | null) =>
    value === null ? min === null && max === null : (min === null || min <= value) && (max === null || max >= value)
  const candidates = references.filter((r) =>
    r.species === p.species
    && fits(p.breed, r.criteria.breed) && fits(p.category, r.criteria.category)
    && fits(p.physiological_stage, r.criteria.physiological_stage) && fits(p.objective, r.criteria.objective)
    && inRange(p.weight_kg, r.criteria.weight_min_kg, r.criteria.weight_max_kg)
    && inRange(p.age_months, r.criteria.age_min_months, r.criteria.age_max_months))
  const specificity = (r: PackReference) => Object.values(r.criteria).filter((v) => v !== null).length
  return candidates.sort((a, b) => specificity(b) - specificity(a) || b.id - a.id)[0] ?? null
}

export interface OfflineEstimate {
  reference: PackReference | null
  group: PackGroup
  result: OfflineResult
  notes: string[]
}

/** Estimation hors ligne pour un lot, avec les mêmes données et règles que le calcul en ligne. */
export function estimateForGroup(pack: OfflinePack, groupId: number, objective: number | null, ingredientIds: number[], mode: Mode = 'ECONOMIC'): OfflineEstimate | null {
  const group = pack.groups.find((g) => g.id === groupId)
  if (!group) return null
  const notes = [...group.profile_notes]
  const reference = matchReference(pack.references, { ...group, objective })
  if (!reference) {
    const result: OfflineResult = {
      status: 'REFUSED', mode, items: [], dm_intake_kg_day: null, as_fed_kg_day: null, cost_per_day: null, cost_per_kg_as_fed: null, currency: 'XOF',
      checks: [], warnings: [], excluded: [],
      refusal_reasons: [pack.is_demo ? t('Aucune référence DEMO ne correspond à ce profil.')
        : t("Aucune référence nutritionnelle validée ne correspond à ce profil d'animal (espèce, catégorie, stade, objectif, poids, âge). Un expert doit d'abord saisir et valider une référence sourcée.")],
    }
    return { reference: null, group, result, notes }
  }
  notes.push(t('Référence retenue automatiquement : « {{name}} ».', { name: reference.name }), ...reference.warnings)
  const result = formulateOffline(restrictProblem(reference.problem, ingredientIds, mode))
  return { reference, group, result, notes: [...notes, ...result.warnings] }
}
