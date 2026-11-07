import { describe, expect, it } from 'vitest'
import { buildCalculationPayload } from './payload'

const base = {
  farm: 1, name: ' Embouche ', mode: 'ECONOMIC' as const, target: 'profile' as const, animal: '', group: '', species: '1',
  category: '4', stage: '', objective: '', weight: '32,5', age: '', reference: '', animals: '', days: '',
  choices: {
    5: { selected: true, price: '', available: '' },
    7: { selected: true, price: '180,5', available: '' },
    9: { selected: false, price: '999', available: '10' },
  },
}

describe('buildCalculationPayload', () => {
  it('ne transmet que les ingrédients cochés et convertit la virgule décimale', () => {
    const p = buildCalculationPayload(base)
    expect(p.name).toBe('Embouche')
    expect(p.ingredients).toEqual([{ ingredient: 5 }, { ingredient: 7, price_per_kg_as_fed: '180.5' }])
    expect(p.animal_weight_kg).toBe('32.5')
    expect(p.category).toBe(4)
    expect(p.reference).toBeNull()
    expect(p.species).toBe(1)
  })

  it('pour un animal, laisse le serveur reprendre le profil de sa fiche', () => {
    const p = buildCalculationPayload({ ...base, target: 'animal', animal: '12', weight: '' })
    expect(p.animal).toBe(12)
    expect(p.species).toBeUndefined()
    expect(p.animal_weight_kg).toBeNull()
  })

  it('ajoute effectif et durée seulement si une disponibilité est saisie', () => {
    expect(buildCalculationPayload(base).number_of_animals).toBeUndefined()
    const p = buildCalculationPayload({ ...base, animals: '20', days: '30', choices: { 5: { selected: true, price: '', available: '300' } } })
    expect(p.ingredients[0]).toEqual({ ingredient: 5, available_kg_as_fed: '300' })
    expect(p.number_of_animals).toBe(20)
    expect(p.duration_days).toBe(30)
  })
})
