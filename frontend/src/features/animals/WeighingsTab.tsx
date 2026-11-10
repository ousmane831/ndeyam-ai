import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Scale, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { WeightChart } from '@/components/LazyChart'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, Card, EmptyState } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { td, th } from '@/components/ui/Layout'
import { ConfirmDialog } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { isOnline } from '@/features/offline/connectivity'
import { isNetworkError, outbox } from '@/features/offline/outbox'
import { animalService, weighingService } from '@/services/animals'
import type { Animal, Weighing } from '@/types/animal'
import { tk } from '@/i18n'
import { applyServerErrors } from '@/utils/forms'
import { METHOD_OPTIONS } from './constants'
import { formatDate, formatNumber, todayIso } from '@/utils/format'


const schema = z.object({
  weighed_on: z.string().min(1, tk('Date obligatoire.')).refine((v) => v <= todayIso(), tk('La date ne peut pas être dans le futur.')),
  weight_kg: z
    .string()
    .trim()
    .refine((v) => Number(v.replace(',', '.')) > 0, tk('Poids positif attendu (kg).')),
  method: z.enum(['SCALE', 'TAPE', 'VISUAL']),
  observations: z.string(),
})
type Values = z.infer<typeof schema>

function AdgValue({ value }: { value: string | null }) {
  const { t } = useTranslation()
  if (value === null) return <span className="text-slate-500">—</span>
  const n = Number(value)
  return <span className={n < 0 ? 'text-red-700' : ''}>{t('{{value}} g/j', { value: formatNumber(n, 1) })}</span>
}

export function WeighingsTab({ animal, canWrite }: { animal: Animal; canWrite: boolean }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const growth = useQuery({ queryKey: ['growth', animal.id], queryFn: () => animalService.growth(animal.id) })
  const weighings = useQuery({ queryKey: ['weighings', animal.id], queryFn: () => weighingService.list({ animal: animal.id, page_size: 100 }) })
  const [serverError, setServerError] = useState<string | null>(null)
  const [offlineNote, setOfflineNote] = useState<string | null>(null)
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
    setOfflineNote(null)
    const payload = { ...values, animal: animal.id, weight_kg: values.weight_kg.replace(',', '.') }
    // Sans réseau, la pesée est gardée sur l'appareil et envoyée au retour de la connexion.
    const keepForLater = () => {
      outbox.add({
        kind: 'weighing',
        payload,
        label: t('Pesée de {{tag}} ({{weight}} kg, {{date}})', { tag: animal.tag_number, weight: payload.weight_kg.replace('.', ','), date: formatDate(values.weighed_on) }),
      })
      reset({ ...values, weight_kg: '', observations: '' })
      setOfflineNote(t('Hors ligne : pesée gardée sur cet appareil, envoyée automatiquement au retour du réseau.'))
    }
    if (!isOnline()) return keepForLater()
    try {
      await weighingService.create(payload)
      reset({ ...values, weight_kg: '', observations: '' })
      refresh()
    } catch (error) {
      if (isNetworkError(error)) return keepForLater()
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
        <Card title={t('Nouvelle pesée')}>
          <form onSubmit={onSubmit} noValidate className="space-y-4">
            {serverError && <Alert tone="error">{serverError}</Alert>}
            {offlineNote && <Alert tone="success">{offlineNote}</Alert>}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <TextField label={t('Date')} type="date" max={todayIso()} required error={errors.weighed_on?.message} {...register('weighed_on')} />
              <TextField label={t('Poids (kg)')} inputMode="decimal" required error={errors.weight_kg?.message} {...register('weight_kg')} />
              <SelectField label={t('Méthode')} options={METHOD_OPTIONS.map((o) => ({ ...o, label: t(o.label) }))} {...register('method')} />
              <TextField label={t('Observation')} {...register('observations')} />
            </div>
            <div className="flex justify-end">
              <Button type="submit" loading={isSubmitting} icon={<Scale className="size-4" />}>
                {t('Enregistrer la pesée')}
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card title={t('Évolution du poids')}>
        {growth.isPending ? (
          <Spinner />
        ) : growth.isError ? (
          <Alert tone="error">{growth.error.message}</Alert>
        ) : g!.points.length === 0 ? (
          <EmptyState icon={<Scale className="size-10" />} title={t('Aucune mesure de poids')}>
            {t('Enregistrez une première pesée pour suivre la croissance de cet animal.')}
          </EmptyState>
        ) : (
          <div className="space-y-5">
            <WeightChart growth={g!} />
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs font-medium text-slate-500 uppercase">{t('GMD sur la période')}</p>
                <p className="mt-1 text-xl font-semibold text-slate-900">
                  <AdgValue value={g!.overall?.adg_g_per_day ?? null} />
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {g!.overall
                    ? t('{{from}} → {{to}} ({{days}} j)', { from: formatDate(g!.overall.from), to: formatDate(g!.overall.to), days: g!.overall.days })
                    : g!.unavailable_reason}
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs font-medium text-slate-500 uppercase">{t('Dernier intervalle')}</p>
                <p className="mt-1 text-xl font-semibold text-slate-900">
                  <AdgValue value={g!.latest_interval?.adg_g_per_day ?? null} />
                </p>
                {g!.latest_vs_range && (
                  <p className="mt-1">
                    <Badge tone={g!.latest_vs_range === 'within' ? 'brand' : 'warning'}>
                      {g!.latest_vs_range === 'within'
                        ? t('Dans la plage de suivi')
                        : g!.latest_vs_range === 'below'
                          ? t('Sous la plage de suivi')
                          : t('Au-dessus de la plage de suivi')}
                    </Badge>
                  </p>
                )}
              </div>
              <div className="rounded-lg bg-slate-50 p-4 text-xs text-slate-600">
                <p className="font-medium text-slate-700">{g!.formula}</p>
                <p className="mt-2">{g!.monitoring_note}</p>
                {g!.monitoring_range && (
                  <p className="mt-1">
                    {t('Plage « {{name}} » : {{min}} à {{max}} g/j (source : {{source}}).', {
                      name: g!.monitoring_range.name,
                      min: g!.monitoring_range.adg_min_g ?? '—',
                      max: g!.monitoring_range.adg_max_g ?? '—',
                      source: g!.monitoring_range.source,
                    })}
                  </p>
                )}
              </div>
            </div>
            {g!.intervals.some((i) => i.low_reliability) && (
              <Alert tone="info">{t('Certaines mesures sont des estimations visuelles : les GMD correspondants sont moins fiables.')}</Alert>
            )}
          </div>
        )}
      </Card>

      <Card title={t('Historique des pesées')}>
        {weighings.isPending ? (
          <Spinner />
        ) : weighings.isError ? (
          <Alert tone="error">{weighings.error.message}</Alert>
        ) : weighings.data.results.length === 0 ? (
          <p className="text-sm text-slate-500">
            {animal.initial_weight_kg
              ? t('Aucune pesée enregistrée (poids initial déclaré : {{weight}} kg).', { weight: formatNumber(animal.initial_weight_kg) })
              : t('Aucune pesée enregistrée.')}
          </p>
        ) : (
          <div className="-mx-5 overflow-x-auto">
            <table className="w-full">
              <thead className="border-y border-slate-200 bg-slate-50">
                <tr>
                  <th className={th}>{t('Date')}</th>
                  <th className={th}>{t('Poids')}</th>
                  <th className={th}>{t('Méthode')}</th>
                  <th className={th}>{t('Observation')}</th>
                  <th className={th}>{t('Saisie par')}</th>
                  {canWrite && <th className={th} />}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {weighings.data.results.map((w) => (
                  <tr key={w.id}>
                    <td className={td}>{formatDate(w.weighed_on)}</td>
                    <td className={`${td} font-medium`}>{formatNumber(w.weight_kg, 2)} kg</td>
                    <td className={td}>{t(w.method_label)}</td>
                    <td className={td}>{w.observations || '—'}</td>
                    <td className={td}>{w.recorded_by_email ?? '—'}</td>
                    {canWrite && (
                      <td className={`${td} text-right`}>
                        <button
                          type="button"
                          onClick={() => setToDelete(w)}
                          className="rounded-md p-2.5 text-slate-500 hover:bg-red-50 hover:text-red-600"
                          aria-label={t('Supprimer la pesée du {{date}}', { date: formatDate(w.weighed_on) })}
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
        title={t('Supprimer cette pesée ?')}
        message={t('Pesée du {{date}} : {{weight}} kg. Le GMD sera recalculé.', { date: formatDate(toDelete?.weighed_on), weight: formatNumber(toDelete?.weight_kg, 2) })}
        confirmLabel={t('Supprimer')}
        danger
        loading={removal.isPending}
        onConfirm={() => toDelete && removal.mutate(toDelete)}
        onCancel={() => setToDelete(null)}
      />
    </div>
  )
}
