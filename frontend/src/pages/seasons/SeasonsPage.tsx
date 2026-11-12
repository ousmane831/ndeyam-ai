import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { Droplets, Lightbulb, Plus, Save } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/Button'
import { Alert, Card, EmptyState, Stamp } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { PageHeader } from '@/components/ui/Layout'
import { Spinner } from '@/components/ui/Spinner'
import { IngredientIcon } from '@/features/formulation/IngredientIcon'
import { plainName } from '@/features/formulation/rationText'
import { ValidationBadge, WorkflowActions } from '@/features/reference/Workflow'
import { SeasonCalendar, SeasonIcon } from '@/features/seasons/SeasonCalendar'
import { seasonTone } from '@/features/seasons/seasonStyle'
import { useFarm } from '@/hooks/useFarm'
import { useRoles } from '@/hooks/useRoles'
import { tk } from '@/i18n'
import { ApiError } from '@/services/api'
import { ingredientService, priceService, sourceService } from '@/services/nutrition'
import { adviceService, availabilityService, seasonService } from '@/services/seasons'
import type { AvailabilityLevel, Season, SeasonalAdvice } from '@/types/season'
import { formatMoney } from '@/utils/format'

const LEVELS: { value: '' | AvailabilityLevel; label: string }[] = [
  { value: '', label: tk('Non précisé') },
  { value: 'ABUNDANT', label: tk('Abondant') },
  { value: 'AVAILABLE', label: tk('Disponible') },
  { value: 'SCARCE', label: tk('Rare') },
  { value: 'UNAVAILABLE', label: tk('Indisponible') },
]
const TOPICS = [
  { value: 'WATER', label: tk('Eau') },
  { value: 'FEED', label: tk('Alimentation') },
  { value: 'SCHEDULE', label: tk('Horaires') },
  { value: 'HOUSING', label: tk('Abri et ombre') },
  { value: 'OTHER', label: tk('Autre') },
]
const errorText = (e: unknown, fallback: string) => (e instanceof ApiError ? [e.message, ...Object.values(e.fieldErrors).flat()].join(' ') : fallback)

/** Disponibilité et prix habituel de chaque aliment pour une saison (déclarés par l'exploitation). */
function AvailabilityTable({ season, farmId, demo }: { season: Season; farmId: number; demo: boolean }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const ingredients = useQuery({ queryKey: ['ingredients-all'], queryFn: ingredientService.all })
  const availability = useQuery({ queryKey: ['availability', farmId, season.id], queryFn: () => availabilityService.list({ farm: farmId, season: season.id }) })
  const prices = useQuery({ queryKey: ['prices', 'season', farmId, season.id], queryFn: () => priceService.list({ farm: farmId, season: season.id }) })
  const [draftPrice, setDraftPrice] = useState<Record<number, string>>({})
  const [message, setMessage] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)

  const items = (ingredients.data ?? []).filter((i) => (i.farm === null || i.farm === farmId) && i.is_demo === demo)
  const levelOf = useMemo(() => new Map((availability.data ?? []).map((a) => [a.ingredient, a])), [availability.data])
  const seasonalPrice = useMemo(() => {
    const map = new Map<number, string>()
    for (const p of [...(prices.data ?? [])].filter((x) => x.season === season.id).sort((a, b) => a.valid_from.localeCompare(b.valid_from))) map.set(p.ingredient, p.price_per_kg_as_fed)
    return map
  }, [prices.data, season.id])

  const setLevel = useMutation({
    mutationFn: async ({ ingredient, level }: { ingredient: number; level: '' | AvailabilityLevel }) => {
      const current = levelOf.get(ingredient)
      if (!level) return current ? availabilityService.remove(current.id) : undefined
      return current ? availabilityService.update(current.id, level) : availabilityService.create({ farm: farmId, ingredient, season: season.id, level })
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['availability', farmId] }),
    onError: (e) => setMessage({ tone: 'error', text: errorText(e, t('Enregistrement impossible.')) }),
  })
  const savePrice = useMutation({
    mutationFn: (ingredient: number) =>
      priceService.create({ farm: farmId, ingredient, season: season.id, price_per_kg_as_fed: draftPrice[ingredient].replace(',', '.') }),
    onSuccess: (_d, ingredient) => {
      setDraftPrice((s) => ({ ...s, [ingredient]: '' }))
      setMessage({ tone: 'success', text: t('Prix de saison enregistré.') })
      queryClient.invalidateQueries({ queryKey: ['prices'] })
    },
    onError: (e) => setMessage({ tone: 'error', text: errorText(e, t('Enregistrement impossible.')) }),
  })

  if (ingredients.isPending || availability.isPending) return <Spinner />
  if (items.length === 0) return <EmptyState title={t('Aucun aliment')} />
  return (
    <div className="space-y-3">
      {message && <Alert tone={message.tone}>{message.text}</Alert>}
      <ul className="divide-y divide-slate-100 border-y border-slate-200">
        {items.map((i) => {
          const level = levelOf.get(i.id)?.level ?? ''
          const price = seasonalPrice.get(i.id)
          return (
            <li key={i.id} className="grid gap-3 py-3 sm:grid-cols-[minmax(0,1fr)_11rem_15rem] sm:items-center">
              <span className="flex min-w-0 items-center gap-3">
                <IngredientIcon category={i.category_code} />
                <span className="min-w-0">
                  <span className="block font-medium text-slate-900">{plainName(i.name)}</span>
                  <span className="text-sm text-slate-500">{price ? t('Prix habituel : {{price}} / kg', { price: formatMoney(price) }) : t('Aucun prix de saison')}</span>
                </span>
              </span>
              <select aria-label={t('Disponibilité de {{name}}', { name: plainName(i.name) })} value={level}
                onChange={(e) => setLevel.mutate({ ingredient: i.id, level: e.target.value as '' | AvailabilityLevel })}
                className={clsx('h-11 rounded-md border px-3 text-sm', level === 'SCARCE' ? 'border-mil-500 bg-mil-50' : level === 'UNAVAILABLE' ? 'border-red-300 bg-red-50' : 'border-slate-300 bg-white')}>
                {LEVELS.map((l) => <option key={l.value} value={l.value}>{t(l.label)}</option>)}
              </select>
              <span className="flex gap-2">
                <input aria-label={t('Prix habituel de {{name}} en FCFA par kg', { name: plainName(i.name) })} inputMode="decimal" placeholder={t('Prix (FCFA/kg)')}
                  value={draftPrice[i.id] ?? ''} onChange={(e) => setDraftPrice((s) => ({ ...s, [i.id]: e.target.value }))}
                  className="h-11 w-full min-w-0 rounded-md border border-slate-300 px-3 text-sm tabular-nums" />
                <Button variant="secondary" aria-label={t('Enregistrer le prix de {{name}}', { name: plainName(i.name) })} disabled={!(draftPrice[i.id] ?? '').trim()}
                  loading={savePrice.isPending && savePrice.variables === i.id} onClick={() => savePrice.mutate(i.id)} icon={<Save className="size-4" />} />
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function AdviceForm({ season, onDone }: { season: Season; onDone: () => void }) {
  const { t } = useTranslation()
  const sources = useQuery({ queryKey: ['sources'], queryFn: () => sourceService.list({}) })
  const [values, setValues] = useState({ topic: 'WATER', title: '', text: '', source: '' })
  const [error, setError] = useState<string | null>(null)
  const create = useMutation({
    mutationFn: () => adviceService.create({ season: season.id, topic: values.topic, title: values.title.trim(), text: values.text.trim(), source: values.source ? Number(values.source) : null }),
    onSuccess: onDone,
    onError: (e) => setError(errorText(e, t('Enregistrement impossible.'))),
  })
  const set = (k: keyof typeof values) => (e: { target: { value: string } }) => setValues((v) => ({ ...v, [k]: e.target.value }))
  return (
    <div className="space-y-3 rounded-md border border-slate-200 p-4">
      {error && <Alert tone="error">{error}</Alert>}
      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField label={t('Thème')} value={values.topic} onChange={set('topic')} options={TOPICS.map((o) => ({ value: o.value, label: t(o.label) }))} />
        <SelectField label={t('Source')} value={values.source} onChange={set('source')}
          options={[{ value: '', label: t('Aucune (à compléter avant validation)') }, ...(sources.data?.results ?? []).map((s) => ({ value: String(s.id), label: s.title }))]} />
      </div>
      <TextField label={t('Titre')} value={values.title} onChange={set('title')} />
      <label className="block text-sm font-medium text-slate-700">
        {t('Conseil')}
        <textarea rows={3} value={values.text} onChange={set('text')} className="mt-1.5 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </label>
      <div className="flex justify-end">
        <Button loading={create.isPending} disabled={!values.title.trim() || !values.text.trim()} onClick={() => create.mutate()}>{t('Ajouter le conseil')}</Button>
      </div>
    </div>
  )
}

/** Conseils de saison : les éleveurs ne voient que les conseils validés ; les experts les rédigent et les valident. */
function AdviceList({ season, demo }: { season: Season; demo: boolean }) {
  const { t } = useTranslation()
  const { isReviewer } = useRoles()
  const queryClient = useQueryClient()
  const [adding, setAdding] = useState(false)
  const advice = useQuery({ queryKey: ['advice', season.id], queryFn: () => adviceService.list({ season: season.id }) })
  const visible = (advice.data ?? []).filter((a: SeasonalAdvice) =>
    isReviewer || (demo ? a.is_demo && a.status !== 'REJECTED' : !a.is_demo && a.status === 'VALIDATED'))
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['advice'] })

  return (
    <div className="space-y-3">
      {advice.isPending ? <Spinner /> : visible.length === 0 ? (
        <p className="text-sm text-slate-600">{t('Aucun conseil validé pour cette saison. Les conseils sont publiés après validation par un spécialiste.')}</p>
      ) : (
        <ul className="space-y-3">
          {visible.map((a) => (
            <li key={a.id} className="rounded-md border border-slate-200 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="flex items-center gap-2 font-semibold text-slate-900">
                  {a.topic === 'WATER' ? <Droplets className="size-5 text-brand-600" aria-hidden /> : <Lightbulb className="size-5 text-mil-600" aria-hidden />}
                  {a.title}
                </p>
                <span className="flex min-w-0 flex-wrap items-center gap-2">
                  <Stamp tone="neutral">{t(a.topic_label)}</Stamp>
                  {(isReviewer || a.is_demo) && <ValidationBadge status={a.status} isDemo={a.is_demo} />}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-700">{a.text}</p>
              {isReviewer && (
                <div className="mt-3">
                  <WorkflowActions status={a.status} canSubmit isReviewer onAction={async (action, comment) => { await adviceService.transition(a.id, action, comment); refresh() }} />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {isReviewer && (adding
        ? <AdviceForm season={season} onDone={() => { setAdding(false); refresh() }} />
        : <Button variant="secondary" size="sm" icon={<Plus className="size-4" />} onClick={() => setAdding(true)}>{t('Rédiger un conseil')}</Button>)}
    </div>
  )
}

export function SeasonsPage() {
  const { t } = useTranslation()
  const { selectedFarmId, writableFarms, farms } = useFarm()
  const seasons = useQuery({ queryKey: ['seasons'], queryFn: seasonService.list, staleTime: Infinity })
  const current = useQuery({ queryKey: ['season-current', selectedFarmId], queryFn: () => seasonService.current(selectedFarmId) })
  const [chosen, setChosen] = useState<number | null>(null)
  const list = seasons.data ?? []
  const season = list.find((s) => s.id === chosen) ?? list.find((s) => s.id === current.data?.season?.id) ?? list[0]
  const farm = writableFarms.find((f) => f.id === selectedFarmId) ?? writableFarms[0]
  const demo = Boolean((farms.find((f) => f.id === selectedFarmId) ?? farm)?.is_demo)

  if (seasons.isPending) return <Spinner />
  return (
    <div className="space-y-6">
      <PageHeader title={t('Saisons')} description={t("Prix et disponibilité des aliments selon la période, et conseils de saison validés par un spécialiste. Le calendrier est indicatif et peut être ajusté selon la zone.")} />
      <Card title={t('Calendrier')}>
        <SeasonCalendar seasons={list} />
        {current.data?.season && (
          <p className="mt-4 text-sm text-slate-700">
            {t('Saison en cours : {{season}}.', { season: t(current.data.season.name) })} {t(current.data.season.description)}
          </p>
        )}
      </Card>

      <div className="flex flex-wrap gap-2" role="tablist" aria-label={t('Saison')}>
        {list.map((s) => (
          <button key={s.id} type="button" role="tab" aria-selected={s.id === season?.id} onClick={() => setChosen(s.id)}
            className={clsx('inline-flex min-h-11 items-center gap-2 rounded-full border px-4 text-sm font-semibold',
              s.id === season?.id ? `${seasonTone(s)} border-transparent` : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50')}>
            <SeasonIcon season={s} className="size-4" /> {t(s.name)}
          </button>
        ))}
      </div>

      {season && (
        <>
          <Card title={t('Conseils de saison')}><AdviceList season={season} demo={demo} /></Card>
          <Card title={t('Disponibilité et prix habituels')}>
            {farm ? (
              <>
                <p className="mb-4 text-sm text-slate-600">
                  {t('Indiquez, pour {{season}}, si chaque aliment est facile ou difficile à trouver et son prix habituel. La formule rapide le signale, et le calcul utilise le prix de la saison.', { season: t(season.name).toLowerCase() })}
                </p>
                <AvailabilityTable key={`${farm.id}-${season.id}`} season={season} farmId={farm.id} demo={Boolean(farm.is_demo)} />
              </>
            ) : <p className="text-sm text-slate-600">{t('Réservé aux propriétaires et gestionnaires d’exploitation.')}</p>}
          </Card>
        </>
      )}
    </div>
  )
}
