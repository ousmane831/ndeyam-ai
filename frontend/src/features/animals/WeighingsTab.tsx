import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Scale, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { WeightChart } from '@/components/LazyChart'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, Card, EmptyState } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { td, th } from '@/components/ui/Layout'
import { ConfirmDialog } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { animalService, weighingService } from '@/services/animals'
import type { Animal, Weighing } from '@/types/animal'
import { applyServerErrors } from '@/utils/forms'
import { METHOD_OPTIONS } from './constants'
import { formatDate, formatNumber, todayIso } from '@/utils/format'


const schema = z.object({
  weighed_on: z.string().min(1, 'Date obligatoire.').refine((v) => v <= todayIso(), 'La date ne peut pas être dans le futur.'),
  weight_kg: z
    .string()
    .trim()
    .refine((v) => Number(v.replace(',', '.')) > 0, 'Poids positif attendu (kg).'),
  method: z.enum(['SCALE', 'TAPE', 'VISUAL']),
  observations: z.string(),
})
type Values = z.infer<typeof schema>

function AdgValue({ value }: { value: string | null }) {
  if (value === null) return <span className="text-slate-400">—</span>
  const n = Number(value)
  return <span className={n < 0 ? 'text-red-700' : ''}>{formatNumber(n, 1)} g/j</span>
}

export function WeighingsTab({ animal, canWrite }: { animal: Animal; canWrite: boolean }) {
  const queryClient = useQueryClient()
  const growth = useQuery({ queryKey: ['growth', animal.id], queryFn: () => animalService.growth(animal.id) })
  const weighings = useQuery({ queryKey: ['weighings', animal.id], queryFn: () => weighingService.list({ animal: animal.id, page_size: 100 }) })
  const [serverError, setServerError] = useState<string | null>(null)
  const [toDelete, setToDelete] = useState<Weighing | null>(null)

  const refresh = () => {
    for (const key of [['growth', animal.id], ['weighings', animal.id], ['animal', animal.id], ['animals'], ['alerts'], ['dashboard']]) {
      queryClient.invalidateQueries({ queryKey: key })
    }
  }

  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { weighed_on: todayIso(), weight_kg: '', method: 'SCALE', observations: '' } })

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      await weighingService.create({ ...values, animal: animal.id, weight_kg: values.weight_kg.replace(',', '.') })
      reset({ ...values, weight_kg: '', observations: '' })
      refresh()
    } catch (error) {
      setServerError(applyServerErrors(error, setError, ['weighed_on', 'weight_kg', 'method', 'observations']))
    }
  })

  const removal = useMutation({
    mutationFn: (w: Weighing) => weighingService.remove(w.id),
    onSuccess: () => {
      setToDelete(null)
      refresh()
    },
  })

  const g = growth.data
  return (
    <div className="space-y-6">
      {canWrite && animal.status === 'ACTIVE' && (
        <Card title="Nouvelle pesée">
          <form onSubmit={onSubmit} noValidate className="space-y-4">
            {serverError && <Alert tone="error">{serverError}</Alert>}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <TextField label="Date" type="date" max={todayIso()} required error={errors.weighed_on?.message} {...register('weighed_on')} />
              <TextField label="Poids (kg)" inputMode="decimal" required error={errors.weight_kg?.message} {...register('weight_kg')} />
              <SelectField label="Méthode" options={METHOD_OPTIONS} {...register('method')} />
              <TextField label="Observation" {...register('observations')} />
            </div>
            <div className="flex justify-end">
              <Button type="submit" loading={isSubmitting} icon={<Scale className="size-4" />}>
                Enregistrer la pesée
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card title="Évolution du poids">
        {growth.isPending ? (
          <Spinner />
        ) : growth.isError ? (
          <Alert tone="error">{growth.error.message}</Alert>
        ) : g!.points.length === 0 ? (
          <EmptyState icon={<Scale className="size-10" />} title="Aucune mesure de poids">
            Enregistrez une première pesée pour suivre la croissance de cet animal.
          </EmptyState>
        ) : (
          <div className="space-y-5">
            <WeightChart growth={g!} />
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs font-medium text-slate-500 uppercase">GMD sur la période</p>
                <p className="mt-1 text-xl font-semibold text-slate-900">
                  <AdgValue value={g!.overall?.adg_g_per_day ?? null} />
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {g!.overall ? `${formatDate(g!.overall.from)} → ${formatDate(g!.overall.to)} (${g!.overall.days} j)` : g!.unavailable_reason}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs font-medium text-slate-500 uppercase">Dernier intervalle</p>
                <p className="mt-1 text-xl font-semibold text-slate-900">
                  <AdgValue value={g!.latest_interval?.adg_g_per_day ?? null} />
                </p>
                {g!.latest_vs_range && (
                  <p className="mt-1">
                    <Badge tone={g!.latest_vs_range === 'within' ? 'brand' : 'warning'}>
                      {g!.latest_vs_range === 'within' ? 'Dans la plage de suivi' : g!.latest_vs_range === 'below' ? 'Sous la plage de suivi' : 'Au-dessus de la plage de suivi'}
                    </Badge>
                  </p>
                )}
              </div>
              <div className="rounded-lg bg-slate-50 p-4 text-xs text-slate-600">
                <p className="font-medium text-slate-700">{g!.formula}</p>
                <p className="mt-2">{g!.monitoring_note}</p>
                {g!.monitoring_range && (
                  <p className="mt-1">
                    Plage « {g!.monitoring_range.name} » : {g!.monitoring_range.adg_min_g ?? '—'} à {g!.monitoring_range.adg_max_g ?? '—'} g/j
                    (source : {g!.monitoring_range.source}).
                  </p>
                )}
              </div>
            </div>
            {g!.intervals.some((i) => i.low_reliability) && (
              <Alert tone="info">Certaines mesures sont des estimations visuelles : les GMD correspondants sont moins fiables.</Alert>
            )}
          </div>
        )}
      </Card>

      <Card title="Historique des pesées">
        {weighings.isPending ? (
          <Spinner />
        ) : weighings.isError ? (
          <Alert tone="error">{weighings.error.message}</Alert>
        ) : weighings.data.results.length === 0 ? (
          <p className="text-sm text-slate-500">
            Aucune pesée enregistrée{animal.initial_weight_kg ? ` (poids initial déclaré : ${formatNumber(animal.initial_weight_kg)} kg)` : ''}.
          </p>
        ) : (
          <div className="-mx-5 overflow-x-auto">
            <table className="w-full">
              <thead className="border-y border-slate-200 bg-slate-50">
                <tr>
                  <th className={th}>Date</th>
                  <th className={th}>Poids</th>
                  <th className={th}>Méthode</th>
                  <th className={th}>Observation</th>
                  <th className={th}>Saisie par</th>
                  {canWrite && <th className={th} />}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {weighings.data.results.map((w) => (
                  <tr key={w.id}>
                    <td className={td}>{formatDate(w.weighed_on)}</td>
                    <td className={`${td} font-medium`}>{formatNumber(w.weight_kg, 2)} kg</td>
                    <td className={td}>{w.method_label}</td>
                    <td className={td}>{w.observations || '—'}</td>
                    <td className={td}>{w.recorded_by_email ?? '—'}</td>
                    {canWrite && (
                      <td className={`${td} text-right`}>
                        <button
                          type="button"
                          onClick={() => setToDelete(w)}
                          className="rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                          aria-label={`Supprimer la pesée du ${formatDate(w.weighed_on)}`}
                        >
                          <Trash2 className="size-4" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={toDelete !== null}
        title="Supprimer cette pesée ?"
        message={`Pesée du ${formatDate(toDelete?.weighed_on)} : ${formatNumber(toDelete?.weight_kg, 2)} kg. Le GMD sera recalculé.`}
        confirmLabel="Supprimer"
        danger
        loading={removal.isPending}
        onConfirm={() => toDelete && removal.mutate(toDelete)}
        onCancel={() => setToDelete(null)}
      />
    </div>
  )
}
