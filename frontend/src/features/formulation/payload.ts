import type { CalculationPayload } from '@/types/formula'

export interface IngredientChoice {
  selected: boolean
  price: string
  available: string
}

/** Construit la demande envoyée au moteur à partir du formulaire (valeurs vides = non transmises). */
export function buildCalculationPayload(input: {
  farm: number
  name: string
  mode: 'ECONOMIC' | 'BALANCED'
  target: 'animal' | 'group' | 'profile'
  animal: string
  group: string
  species: string
  category: string
  stage: string
  objective: string
  weight: string
  age: string
  reference: string
  animals: string
  days: string
  choices: Record<number, IngredientChoice>
}): CalculationPayload {
  const id = (v: string) => (v ? Number(v) : undefined)
  const dec = (v: string) => (v.trim() ? v.trim().replace(',', '.') : undefined)
  const ingredients = Object.entries(input.choices)
    .filter(([, c]) => c.selected)
    .map(([ingredient, c]) => ({
      ingredient: Number(ingredient),
      ...(dec(c.price) ? { price_per_kg_as_fed: dec(c.price) } : {}),
      ...(dec(c.available) ? { available_kg_as_fed: dec(c.available) } : {}),
    }))
  const payload: CalculationPayload = {
    farm: input.farm,
    name: input.name.trim(),
    mode: input.mode,
    ingredients,
    reference: id(input.reference) ?? null,
    category: id(input.category) ?? null,
    physiological_stage: id(input.stage) ?? null,
    objective: id(input.objective) ?? null,
    animal_weight_kg: dec(input.weight) ?? null,
    animal_age_months: dec(input.age) ?? null,
  }
  if (input.target === 'animal') payload.animal = id(input.animal)
  else payload.species = id(input.species)
  if (input.target === 'group') payload.group = id(input.group)
  if (ingredients.some((i) => 'available_kg_as_fed' in i)) {
    payload.number_of_animals = id(input.animals)
    payload.duration_days = id(input.days)
  }
  return payload
}
