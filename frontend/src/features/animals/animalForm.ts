import { z } from 'zod'
import type { AnimalPayload } from '@/types/animal'
import { tk } from '@/i18n'
import { todayIso } from '@/utils/format'

/** Schéma de validation et conversion du formulaire animal (création et modification). */

const positiveDecimal = (message: string) =>
  z
    .string()
    .trim()
    .refine((v) => v === '' || (!Number.isNaN(Number(v.replace(',', '.'))) && Number(v.replace(',', '.')) > 0), message)

export const animalSchema = z
  .object({
    farm: z.string().min(1, tk("Choisissez l'exploitation.")),
    tag_number: z.string().trim().min(1, tk('Le numéro est obligatoire.')).max(64, tk('64 caractères maximum.')),
    name: z.string().trim().max(120, tk('120 caractères maximum.')),
    species: z.string().min(1, tk("Choisissez l'espèce.")),
    breed: z.string(),
    sex: z.enum(['M', 'F'], { error: tk('Choisissez le sexe.') }),
    birth_mode: z.enum(['date', 'age', 'unknown']),
    birth_date: z.string(),
    estimated_age_months: z.string().trim(),
    initial_weight_kg: positiveDecimal(tk('Poids initial : nombre positif attendu.')),
    category: z.string(),
    physiological_stage: z.string(),
    group: z.string(),
    registered_on: z.string().min(1, tk("La date d'enregistrement est obligatoire.")),
    observations: z.string(),
  })
  .superRefine((v, ctx) => {
    if (v.birth_mode === 'date') {
      if (!v.birth_date) ctx.addIssue({ code: 'custom', path: ['birth_date'], message: tk('Indiquez la date de naissance.') })
      else if (v.birth_date > todayIso()) ctx.addIssue({ code: 'custom', path: ['birth_date'], message: tk('La date ne peut pas être dans le futur.') })
    }
    if (v.birth_mode === 'age') {
      const n = Number(v.estimated_age_months.replace(',', '.'))
      if (!v.estimated_age_months || Number.isNaN(n) || n < 0 || n > 240)
        ctx.addIssue({ code: 'custom', path: ['estimated_age_months'], message: tk('Âge estimé en mois (entre 0 et 240).') })
    }
  })
export type AnimalFormValues = z.infer<typeof animalSchema>

export const ANIMAL_FIELDS = [
  'farm', 'tag_number', 'name', 'species', 'breed', 'sex', 'birth_date', 'estimated_age_months',
  'initial_weight_kg', 'category', 'physiological_stage', 'group', 'registered_on', 'observations',
] as const

const toId = (v: string) => (v ? Number(v) : null)
const dec = (v: string) => (v ? v.replace(',', '.') : null)

export function toPayload(v: AnimalFormValues, editing: boolean): AnimalPayload {
  const payload: AnimalPayload = {
    farm: Number(v.farm),
    tag_number: v.tag_number,
    name: v.name,
    species: Number(v.species),
    breed: toId(v.breed),
    sex: v.sex,
    initial_weight_kg: dec(v.initial_weight_kg),
    category: toId(v.category),
    physiological_stage: toId(v.physiological_stage),
    group: toId(v.group),
    registered_on: v.registered_on,
    observations: v.observations,
  }
  if (v.birth_mode === 'date') payload.birth_date = v.birth_date
  else if (v.birth_mode === 'age') payload.estimated_age_months = dec(v.estimated_age_months)
  else if (editing) payload.birth_date = null
  return payload
}
