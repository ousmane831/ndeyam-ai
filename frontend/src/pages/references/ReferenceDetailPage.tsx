import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, Card, EmptyState } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { DefinitionList, PageHeader, td, th } from '@/components/ui/Layout'
import { Spinner } from '@/components/ui/Spinner'
import { ValidationBadge, WorkflowActions } from '@/features/reference/Workflow'
import { useRoles } from '@/hooks/useRoles'
import { ApiError } from '@/services/api'
import { inclusionService, ingredientService, nutritionService, referenceService, sourceService } from '@/services/nutrition'
import type { NutritionalReference } from '@/types/nutrition'
import { formatDate, formatNumber } from '@/utils/format'

const errorText = (e: unknown, fallback: string) =>
  e instanceof ApiError ? Object.values(e.fieldErrors).flat().join(' ') || e.message : e instanceof Error ? e.message : fallback
const num = (v: string) => (v.trim() ? v.trim().replace(',', '.') : null)

function RequirementForm({ reference, onDone }: { reference: NutritionalReference; onDone: () => void }) {
  const { t } = useTranslation()
  const nutrients = useQuery({ queryKey: ['nutrients'], queryFn: nutritionService.nutrients, staleTime: Infinity })
  // Seuls les nutriments universels et ceux du système de la référence sont proposés (pas de mélange).
  const allowed = (nutrients.data ?? []).filter((n) => n.system === null || n.system === reference.system)
  const [f, setF] = useState({ nutrient: '', expression: 'DAILY_AMOUNT', min: '', target: '', max: '' })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((s) => ({ ...s, [k]: e.target.value }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!f.nutrient) return setError(t('Choisissez le nutriment.'))
    if (!f.min && !f.target && !f.max) return setError(t('Renseignez au moins une valeur.'))
    setBusy(true)
    try {
      await referenceService.addRequirement({ reference: reference.id, nutrient: Number(f.nutrient), expression: f.expression,
        min_value: num(f.min), target_value: num(f.target), max_value: num(f.max) })
      setF({ ...f, nutrient: '', min: '', target: '', max: '' })
      onDone()
    } catch (err) {
      setError(errorText(err, t('Action impossible.')))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-3 rounded-lg border border-dashed border-slate-300 p-4">
      <p className="text-sm font-medium text-slate-800">{t('Ajouter un besoin')}</p>
      {error && <Alert tone="error">{error}</Alert>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <SelectField label={t('Nutriment')} value={f.nutrient} onChange={set('nutrient')}
          options={[{ value: '', label: t('Choisir…') }, ...allowed.filter((n) => n.category !== 'DRY_MATTER' || f.expression !== 'DAILY_AMOUNT')
            .map((n) => ({ value: String(n.id), label: `${n.code}${n.system_code ? ` (${n.system_code})` : ''}` }))]} />
        <SelectField label={t('Expression')} value={f.expression} onChange={set('expression')}
          options={[{ value: 'DAILY_AMOUNT', label: t('Par animal et par jour') }, { value: 'DIET_CONCENTRATION', label: t('Teneur de la ration (/kg MS)') }]} />
        <TextField label={t('Minimum')} inputMode="decimal" value={f.min} onChange={set('min')} />
        <TextField label={t('Cible')} inputMode="decimal" value={f.target} onChange={set('target')} />
        <TextField label={t('Maximum')} inputMode="decimal" value={f.max} onChange={set('max')} />
      </div>
      <div className="flex justify-end"><Button type="submit" size="sm" loading={busy} icon={<Plus className="size-4" />}>{t('Ajouter')}</Button></div>
    </form>
  )
}

function InclusionCard({ reference, isReviewer }: { reference: NutritionalReference; isReviewer: boolean }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const key = ['inclusions', reference.species]
  const list = useQuery({ queryKey: key, queryFn: () => inclusionService.list(reference.species) })
  const categories = useQuery({ queryKey: ['ingredient-categories'], queryFn: nutritionService.categories, staleTime: Infinity })
  const ingredients = useQuery({ queryKey: ['ingredients-all'], queryFn: ingredientService.all, enabled: isReviewer })
  const sources = useQuery({ queryKey: ['sources'], queryFn: () => sourceService.list(), enabled: isReviewer })
  const [target, setTarget] = useState('')
  const [min, setMin] = useState('')
  const [max, setMax] = useState('')
  const [source, setSource] = useState('')
  const [error, setError] = useState<string | null>(null)
  const refresh = () => queryClient.invalidateQueries({ queryKey: key })
  const removal = useMutation({ mutationFn: inclusionService.remove, onSuccess: refresh })

  const add = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!target) return setError(t('Choisissez un ingrédient ou une catégorie.'))
    const [kind, id] = target.split(':')
    try {
      await inclusionService.create({ species: reference.species, [kind === 'i' ? 'ingredient' : 'ingredient_category']: Number(id),
        min_pct_dm: num(min), max_pct_dm: num(max), source: source ? Number(source) : null })
      setMin('')
      setMax('')
      refresh()
    } catch (err) {
      setError(errorText(err, t('Action impossible.')))
    }
  }

  return (
    <Card title={t("Contraintes d'incorporation — {{species}}", { species: t(reference.species_name) })}>
      <div className="space-y-4">
        <p className="text-xs text-slate-500">{t("Bornes en % de la matière sèche de la ration, appliquées par le moteur lorsqu'elles sont validées.")}</p>
        {list.isPending ? <Spinner /> : list.isError ? <Alert tone="error">{list.error.message}</Alert> : list.data.length === 0 ? (
          <p className="text-sm text-slate-500">{t("Aucune contrainte d'incorporation.")}</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {list.data.map((c) => (
              <li key={c.id} className="flex flex-wrap items-start justify-between gap-3 py-3 first:pt-0">
                <div>
                  <p className="text-sm font-medium text-slate-800">{t('{{target}} : {{min}} – {{max}} % MS', { target: t(c.target_label), min: c.min_pct_dm ?? '0', max: c.max_pct_dm ?? '100' })}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <ValidationBadge status={c.status} isDemo={c.is_demo} /> {c.source?.title ?? t('sans source')}
                  </div>
                </div>
                {isReviewer && (
                  <div className="flex items-start gap-2">
                    <WorkflowActions status={c.status} canSubmit isReviewer onAction={(a, comment) => inclusionService.act(c.id, a, comment).then(refresh)} />
                    <button type="button" onClick={() => removal.mutate(c.id)} className="rounded-md p-2.5 text-slate-500 hover:text-red-600" aria-label={t('Supprimer la contrainte')}><Trash2 className="size-4" /></button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        {isReviewer && (
          <form onSubmit={add} noValidate className="space-y-3 rounded-lg border border-dashed border-slate-300 p-4">
            {error && <Alert tone="error">{error}</Alert>}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <SelectField label={t('Ingrédient ou catégorie')} value={target} onChange={(e) => setTarget(e.target.value)} options={[
                { value: '', label: t('Choisir…') },
                ...(categories.data ?? []).map((c) => ({ value: `c:${c.id}`, label: t('Catégorie : {{name}}', { name: t(c.name) }) })),
                ...(ingredients.data ?? []).filter((i) => i.scope === 'catalog').map((i) => ({ value: `i:${i.id}`, label: i.name })),
              ]} />
              <TextField label={t('Min. (% MS)')} inputMode="decimal" value={min} onChange={(e) => setMin(e.target.value)} />
              <TextField label={t('Max. (% MS)')} inputMode="decimal" value={max} onChange={(e) => setMax(e.target.value)} />
              <SelectField label={t('Source')} value={source} onChange={(e) => setSource(e.target.value)}
                options={[{ value: '', label: t('Non renseignée') }, ...(sources.data?.results ?? []).map((s) => ({ value: String(s.id), label: s.title }))]} />
            </div>
            <div className="flex justify-end"><Button type="submit" size="sm" icon={<Plus className="size-4" />}>{t('Ajouter la contrainte')}</Button></div>
          </form>
        )}
      </div>
    </Card>
  )
}

export function ReferenceDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams()
  const refId = Number(id)
  const queryClient = useQueryClient()
  const { isReviewer } = useRoles()
  const reference = useQuery({ queryKey: ['reference', refId], queryFn: () => referenceService.get(refId) })
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['reference', refId] })
    queryClient.invalidateQueries({ queryKey: ['references'] })
  }
  const removeReq = useMutation({ mutationFn: referenceService.removeRequirement, onSuccess: refresh })

  if (reference.isPending) return <Spinner />
  if (reference.isError) return <Alert tone="error">{reference.error.message}</Alert>
  const r = reference.data
  const bound = (a: string | null, b: string | null, unit: string) =>
    a === null && b === null ? t('Non borné') : a !== null && b !== null && Number(a) === Number(b) ? `${a} ${unit}` : `${a ?? '…'} – ${b ?? '…'} ${unit}`

  return (
    <div className="space-y-6">
      <Link to="/references" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"><ArrowLeft className="size-4" /> {t('Références')}</Link>
      <PageHeader title={r.name} description={<span className="flex flex-wrap items-center gap-2">{t('Système {{code}}', { code: r.system_code })} <ValidationBadge status={r.status} isDemo={r.is_demo} /></span>}
        actions={<WorkflowActions status={r.status} canSubmit={isReviewer} isReviewer={isReviewer} onAction={(a, c) => referenceService.act(r.id, a, c).then(refresh)} />} />
      {r.status === 'VALIDATED' && isReviewer && <Alert tone="info">{t('Toute modification des besoins remettra cette référence en brouillon : elle devra être revalidée.')}</Alert>}
      {r.validation_comment && <Alert tone={r.status === 'REJECTED' ? 'warning' : 'info'} title={t('Commentaire de validation')}>{r.validation_comment}</Alert>}

      <Card>
        <DefinitionList items={[
          { label: t('Espèce'), value: t(r.species_name) },
          { label: t('Race'), value: r.breed_name ? t(r.breed_name) : t('Toutes') },
          { label: t('Catégorie'), value: r.category_name ? t(r.category_name) : t('Toutes') },
          { label: t('Stade physiologique'), value: r.physiological_stage_name ? t(r.physiological_stage_name) : t('Tous') },
          { label: t('Objectif'), value: r.objective_name ? t(r.objective_name) : t('Tous') },
          { label: t('Poids'), value: bound(r.weight_min_kg, r.weight_max_kg, 'kg') },
          { label: t('Âge'), value: bound(r.age_min_months, r.age_max_months, t('mois')) },
          { label: t('Ingestion de MS'), value: bound(r.dm_intake_min_kg_day, r.dm_intake_max_kg_day, t('kg MS/j')) },
          { label: t('Source'), value: r.source?.title ?? t('Non renseignée (validation impossible)') },
          { label: t('Validée par'), value: r.validated_by_email ? t('{{email}} le {{date}}', { email: r.validated_by_email, date: formatDate(r.validated_at) }) : '—' },
          { label: t("Conditions d'application"), value: r.application_conditions || '—' },
        ]} />
      </Card>

      <Card title={t('Besoins nutritionnels')}>
        <div className="space-y-4">
          {r.requirements.length === 0 ? <EmptyState title={t('Aucun besoin saisi')}>{t('Une référence sans besoin ne peut pas être validée.')}</EmptyState> : (
            <div className="-mx-5 overflow-x-auto">
              <table className="w-full">
                <thead className="border-y border-slate-200 bg-slate-50"><tr>
                  <th className={th}>{t('Nutriment')}</th><th className={th}>{t('Expression')}</th><th className={th}>{t('Minimum')}</th><th className={th}>{t('Cible')}</th><th className={th}>{t('Maximum')}</th><th className={th}>{t('Unité')}</th>{isReviewer && <th className={th} />}
                </tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {r.requirements.map((q) => (
                    <tr key={q.id}>
                      <td className={td}><span className="font-medium">{q.nutrient_code}</span> <span className="text-xs text-slate-500">{t(q.nutrient_name)}</span></td>
                      <td className={td}>{t(q.expression_label)}</td>
                      <td className={td}>{q.min_value !== null ? formatNumber(q.min_value, 4) : '—'}</td>
                      <td className={td}>{q.target_value !== null ? formatNumber(q.target_value, 4) : '—'}</td>
                      <td className={td}>{q.max_value !== null ? formatNumber(q.max_value, 4) : '—'}</td>
                      <td className={td}>{t(q.unit_label)}</td>
                      {isReviewer && <td className={`${td} text-right`}><button type="button" onClick={() => removeReq.mutate(q.id)} className="rounded-md p-2.5 text-slate-500 hover:text-red-600" aria-label={t('Supprimer le besoin {{code}}', { code: q.nutrient_code })}><Trash2 className="size-4" /></button></td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {isReviewer && <RequirementForm reference={r} onDone={refresh} />}
        </div>
      </Card>

      <InclusionCard reference={r} isReviewer={isReviewer} />
    </div>
  )
}
