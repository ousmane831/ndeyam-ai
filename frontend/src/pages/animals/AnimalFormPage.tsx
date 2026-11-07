import { zodResolver } from '@hookform/resolvers/zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, Card } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { PageHeader } from '@/components/ui/Layout'
import { Spinner } from '@/components/ui/Spinner'
import { useFarm } from '@/hooks/useFarm'
import { animalService, groupService, nomenclatureService } from '@/services/animals'
import { ANIMAL_FIELDS, animalSchema, toPayload, type AnimalFormValues } from '@/features/animals/animalForm'
import type { Animal } from '@/types/animal'
import { applyServerErrors } from '@/utils/forms'
import { todayIso } from '@/utils/format'

function initialValues(animal: Animal | undefined, farm: number | null, species: number | undefined): AnimalFormValues {
  const s = (v: number | null | undefined) => (v ? String(v) : '')
  return {
    farm: animal ? String(animal.farm) : s(farm),
    tag_number: animal?.tag_number ?? '',
    name: animal?.name ?? '',
    species: animal ? String(animal.species) : s(species),
    breed: s(animal?.breed),
    sex: animal?.sex ?? ('' as 'M'),
    birth_mode: animal?.birth_date ? 'date' : 'unknown',
    birth_date: animal?.birth_date ?? '',
    estimated_age_months: '',
    initial_weight_kg: animal?.initial_weight_kg ?? '',
    category: s(animal?.category),
    physiological_stage: s(animal?.physiological_stage),
    group: s(animal?.group),
    registered_on: animal?.registered_on ?? todayIso(),
    observations: animal?.observations ?? '',
  }
}

export function AnimalFormPage() {
  const { id } = useParams()
  const editing = Boolean(id)
  const animal = useQuery({ queryKey: ['animal', Number(id)], queryFn: () => animalService.get(Number(id)), enabled: editing })
  const species = useQuery({ queryKey: ['species'], queryFn: nomenclatureService.species, staleTime: Infinity })

  if ((editing && animal.isPending) || species.isPending) return <Spinner />
  if (animal.isError) return <Alert tone="error">{animal.error.message}</Alert>
  if (species.isError) return <Alert tone="error">{species.error.message}</Alert>
  return <AnimalForm animal={animal.data} defaultSpecies={species.data.length === 1 ? species.data[0].id : undefined} />
}

function AnimalForm({ animal, defaultSpecies }: { animal?: Animal; defaultSpecies?: number }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { writableFarms, defaultWritableFarmId } = useFarm()
  const [serverError, setServerError] = useState<string | null>(null)
  const editing = Boolean(animal)

  const {
    register,
    handleSubmit,
    setError,
    control,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<AnimalFormValues>({
    resolver: zodResolver(animalSchema),
    defaultValues: initialValues(animal, defaultWritableFarmId, defaultSpecies),
  })
  const [farm, speciesId, birthMode] = useWatch({ control, name: ['farm', 'species', 'birth_mode'] })

  const species = useQuery({ queryKey: ['species'], queryFn: nomenclatureService.species, staleTime: Infinity })
  const sid = speciesId ? Number(speciesId) : undefined
  const breeds = useQuery({ queryKey: ['breeds', sid], queryFn: () => nomenclatureService.breeds(sid), enabled: Boolean(sid) })
  const categories = useQuery({ queryKey: ['categories', sid], queryFn: () => nomenclatureService.categories(sid), enabled: Boolean(sid) })
  const stages = useQuery({ queryKey: ['stages', sid], queryFn: () => nomenclatureService.stages(sid), enabled: Boolean(sid) })
  const groups = useQuery({ queryKey: ['groups', Number(farm)], queryFn: () => groupService.list(Number(farm)), enabled: Boolean(farm) })

  // Changer d'espèce invalide la race, la catégorie et le stade déjà choisis.
  useEffect(() => {
    if (animal && String(animal.species) === speciesId) return
    setValue('breed', '')
    setValue('category', '')
    setValue('physiological_stage', '')
  }, [speciesId, animal, setValue])

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      const payload = toPayload(values, editing)
      const saved = animal ? await animalService.update(animal.id, payload) : await animalService.create(payload)
      await queryClient.invalidateQueries({ queryKey: ['animals'] })
      queryClient.setQueryData(['animal', saved.id], saved)
      navigate(`/animaux/${saved.id}`)
    } catch (error) {
      setServerError(applyServerErrors(error, setError, ANIMAL_FIELDS))
    }
  })

  if (writableFarms.length === 0) {
    return <Alert tone="warning">Vous n'avez accès en écriture à aucune exploitation : impossible d'ajouter un animal.</Alert>
  }

  const opt = (items: { id: number; name: string }[] | undefined, empty: string) => [
    { value: '', label: empty },
    ...(items ?? []).map((i) => ({ value: String(i.id), label: i.name })),
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title={animal ? `Modifier ${animal.tag_number}` : 'Ajouter un animal'}
        description="Les champs marqués d'un astérisque sont obligatoires."
      />
      <form onSubmit={onSubmit} noValidate className="space-y-6">
        {serverError && <Alert tone="error">{serverError}</Alert>}

        <Card title="Identification">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {!editing && writableFarms.length > 1 && (
              <SelectField label="Exploitation" required error={errors.farm?.message} options={opt(writableFarms, 'Choisir…')} {...register('farm')} />
            )}
            <TextField label="Numéro / boucle" required error={errors.tag_number?.message} {...register('tag_number')} />
            <TextField label="Nom" error={errors.name?.message} {...register('name')} />
            <SelectField label="Espèce" required error={errors.species?.message} options={opt(species.data, 'Choisir…')} {...register('species')} />
            <SelectField label="Race" options={opt(breeds.data, 'Non renseignée')} {...register('breed')} error={errors.breed?.message} />
            <SelectField
              label="Sexe"
              required
              error={errors.sex?.message}
              options={[
                { value: '', label: 'Choisir…' },
                { value: 'F', label: 'Femelle' },
                { value: 'M', label: 'Mâle' },
              ]}
              {...register('sex')}
            />
          </div>
        </Card>

        <Card title="Âge et poids">
          <div className="space-y-4">
            <fieldset>
              <legend className="mb-2 text-sm font-medium text-slate-700">Âge</legend>
              <div className="flex flex-wrap gap-4 text-sm">
                {[
                  ['date', 'Date de naissance connue'],
                  ['age', 'Âge estimé'],
                  ['unknown', 'Inconnu'],
                ].map(([value, label]) => (
                  <label key={value} className="inline-flex items-center gap-2">
                    <input type="radio" value={value} className="accent-brand-600" {...register('birth_mode')} />
                    {label}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {birthMode === 'date' && (
                <TextField
                  label="Date de naissance"
                  type="date"
                  max={todayIso()}
                  required
                  hint={animal?.birth_date_is_estimated ? 'Date actuellement estimée.' : undefined}
                  error={errors.birth_date?.message}
                  {...register('birth_date')}
                />
              )}
              {birthMode === 'age' && (
                <TextField
                  label="Âge estimé (mois)"
                  inputMode="decimal"
                  required
                  hint="La date de naissance sera calculée et marquée « estimée »."
                  error={errors.estimated_age_months?.message}
                  {...register('estimated_age_months')}
                />
              )}
              <TextField label="Poids initial (kg)" inputMode="decimal" error={errors.initial_weight_kg?.message} {...register('initial_weight_kg')} />
              <TextField label="Date d'enregistrement" type="date" required error={errors.registered_on?.message} {...register('registered_on')} />
            </div>
          </div>
        </Card>

        <Card title="Classement">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <SelectField label="Catégorie" options={opt(categories.data, 'Non renseignée')} error={errors.category?.message} {...register('category')} />
            <SelectField
              label="Stade physiologique"
              options={opt(stages.data, 'Non renseigné')}
              error={errors.physiological_stage?.message}
              {...register('physiological_stage')}
            />
            <SelectField label="Lot" options={opt(groups.data?.results, 'Aucun lot')} error={errors.group?.message} {...register('group')} />
          </div>
          <div className="mt-4 space-y-1.5">
            <label htmlFor="observations" className="block text-sm font-medium text-slate-700">
              Observations
            </label>
            <textarea id="observations" rows={3} className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" {...register('observations')} />
          </div>
        </Card>

        <div className="flex flex-wrap justify-end gap-2">
          <Link
            to={animal ? `/animaux/${animal.id}` : '/animaux'}
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Annuler
          </Link>
          <Button type="submit" loading={isSubmitting}>
            {animal ? 'Enregistrer' : "Ajouter l'animal"}
          </Button>
        </div>
      </form>
    </div>
  )
}
