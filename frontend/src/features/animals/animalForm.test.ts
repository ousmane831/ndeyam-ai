import { describe, expect, it } from 'vitest'
import { todayIso } from '@/utils/format'
import { animalSchema, toPayload, type AnimalFormValues } from './animalForm'

const base: AnimalFormValues = {
  farm: '1', tag_number: 'SN-001', name: '', species: '1', breed: '', sex: 'F', birth_mode: 'unknown', birth_date: '',
  estimated_age_months: '', initial_weight_kg: '', category: '', physiological_stage: '', group: '',
  registered_on: '2026-11-01', observations: '',
}

function errorsOf(values: Partial<AnimalFormValues>) {
  const result = animalSchema.safeParse({ ...base, ...values })
  return result.success ? {} : Object.fromEntries(result.error.issues.map((i) => [i.path.join('.'), i.message]))
}

describe('formulaire animal : validation', () => {
  it('accepte un animal minimal', () => {
    expect(errorsOf({})).toEqual({})
  })

  it('exige numéro, espèce et sexe', () => {
    const errors = errorsOf({ tag_number: ' ', species: '', sex: '' as 'F' })
    expect(Object.keys(errors).sort()).toEqual(['sex', 'species', 'tag_number'])
  })

  it('exige la date de naissance en mode « date » et refuse une date future', () => {
    expect(errorsOf({ birth_mode: 'date' }).birth_date).toMatch(/Indiquez/)
    expect(errorsOf({ birth_mode: 'date', birth_date: '2999-01-01' }).birth_date).toMatch(/futur/)
    expect(errorsOf({ birth_mode: 'date', birth_date: todayIso() })).toEqual({})
  })

  it("contrôle l'âge estimé", () => {
    expect(errorsOf({ birth_mode: 'age', estimated_age_months: '' }).estimated_age_months).toBeDefined()
    expect(errorsOf({ birth_mode: 'age', estimated_age_months: '-2' }).estimated_age_months).toBeDefined()
    expect(errorsOf({ birth_mode: 'age', estimated_age_months: '6,5' })).toEqual({})
  })

  it('refuse un poids nul ou négatif mais accepte la virgule', () => {
    expect(errorsOf({ initial_weight_kg: '0' }).initial_weight_kg).toBeDefined()
    expect(errorsOf({ initial_weight_kg: '28,5' })).toEqual({})
  })
})

describe('formulaire animal : conversion pour l’API', () => {
  it('convertit les identifiants et la virgule décimale', () => {
    const payload = toPayload({ ...base, breed: '3', group: '', initial_weight_kg: '28,5' }, false)
    expect(payload).toMatchObject({ farm: 1, species: 1, breed: 3, group: null, initial_weight_kg: '28.5' })
    expect(payload).not.toHaveProperty('birth_date')
  })

  it("envoie l'âge estimé ou la date selon le mode choisi", () => {
    expect(toPayload({ ...base, birth_mode: 'age', estimated_age_months: '6,5' }, false).estimated_age_months).toBe('6.5')
    expect(toPayload({ ...base, birth_mode: 'date', birth_date: '2026-01-01' }, false).birth_date).toBe('2026-01-01')
  })

  it('efface la date de naissance lorsque l’âge devient inconnu en modification', () => {
    expect(toPayload({ ...base, birth_mode: 'unknown' }, true).birth_date).toBeNull()
  })
})
