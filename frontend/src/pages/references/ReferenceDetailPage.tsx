import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
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

const errorText = (e: unknown) =>
  e instanceof ApiError ? Object.values(e.fieldErrors).flat().join(' ') || e.message : e instanceof Error ? e.message : 'Action impossible.'
const num = (v: string) => (v.trim() ? v.trim().replace(',', '.') : null)

function RequirementForm({ reference, onDone }: { reference: NutritionalReference; onDone: () => void }) {
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
    if (!f.nutrient) return setError('Choisissez le nutriment.')
    if (!f.min && !f.target && !f.max) return setError('Renseignez au moins une valeur.')
    setBusy(true)
    try {
      await referenceService.addRequirement({ reference: reference.id, nutrient: Number(f.nutrient), expression: f.expression,
        min_value: num(f.min), target_value: num(f.target), max_value: num(f.max) })
      setF({ ...f, nutrient: '', min: '', target: '', max: '' })
      onDone()
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-3 rounded-lg border border-dashed border-slate-300 p-4">
      <p className="text-sm font-medium text-slate-800">Ajouter un besoin</p>
      {error && <Alert tone="error">{error}</Alert>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <SelectField label="Nutriment" value={f.nutrient} onChange={set('nutrient')}
          options={[{ value: '', label: 'Choisir…' }, ...allowed.filter((n) => n.category !== 'DRY_MATTER' || f.expression !== 'DAILY_AMOUNT')
            .map((n) => ({ value: String(n.id), label: `${n.code}${n.system_code ? ` (${n.system_code})` : ''}` }))]} />
        <SelectField label="Expression" value={f.expression} onChange={set('expression')}
          options={[{ value: 'DAILY_AMOUNT', label: 'Par animal et par jour' }, { value: 'DIET_CONCENTRATION', label: 'Teneur de la ration (/kg MS)' }]} />
        <TextField label="Minimum" inputMode="decimal" value={f.min} onChange={set('min')} />
        <TextField label="Cible" inputMode="decimal" value={f.target} onChange={set('target')} />
        <TextField label="Maximum" inputMode="decimal" value={f.max} onChange={set('max')} />
      </div>
      <div className="flex justify-end"><Button type="submit" size="sm" loading={busy} icon={<Plus className="size-4" />}>Ajouter</Button></div>
    </form>
  )
}

function InclusionCard({ reference, isReviewer }: { reference: NutritionalReference; isReviewer: boolean }) {
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
    if (!target) return setError("Choisissez un ingrédient ou une catégorie.")
    const [kind, id] = target.split(':')
    try {
      await inclusionService.create({ species: reference.species, [kind === 'i' ? 'ingredient' : 'ingredient_category']: Number(id),
        min_pct_dm: num(min), max_pct_dm: num(max), source: source ? Number(source) : null })
      setMin('')
      setMax('')
      refresh()
    } catch (err) {
      setError(errorText(err))
    }
  }

  return (
    <Card title={`Contraintes d'incorporation — ${reference.species_name}`}>
      <div className="space-y-4">
        <p className="text-xs text-slate-500">Bornes en % de la matière sèche de la ration, appliquées par le moteur lorsqu'elles sont validées.</p>
        {list.isPending ? <Spinner /> : list.isError ? <Alert tone="error">{list.error.message}</Alert> : list.data.length === 0 ? (
          <p className="text-sm text-slate-500">Aucune contrainte d'incorporation.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {list.data.map((c) => (
              <li key={c.id} className="flex flex-wrap items-start justify-between gap-3 py-3 first:pt-0">
                <div>
                  <p className="text-sm font-medium text-slate-800">{c.target_label} : {c.min_pct_dm ?? '0'} – {c.max_pct_dm ?? '100'} % MS</p>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <ValidationBadge status={c.status} isDemo={c.is_demo} /> {c.source?.title ?? 'sans source'}
                  </div>
                </div>
                {isReviewer && (
                  <div className="flex items-start gap-2">
                    <WorkflowActions status={c.status} canSubmit isReviewer onAction={(a, comment) => inclusionService.act(c.id, a, comment).then(refresh)} />
                    <button type="button" onClick={() => removal.mutate(c.id)} className="rounded-md p-2.5 text-slate-500 hover:text-red-600" aria-label="Supprimer la contrainte"><Trash2 className="size-4" /></button>
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
              <SelectField label="Ingrédient ou catégorie" value={target} onChange={(e) => setTarget(e.target.value)} options={[
                { value: '', label: 'Choisir…' },
                ...(categories.data ?? []).map((c) => ({ value: `c:${c.id}`, label: `Catégorie : ${c.name}` })),
                ...(ingredients.data ?? []).filter((i) => i.scope === 'catalog').map((i) => ({ value: `i:${i.id}`, label: i.name })),
              ]} />
              <TextField label="Min. (% MS)" inputMode="decimal" value={min} onChange={(e) => setMin(e.target.value)} />
              <TextField label="Max. (% MS)" inputMode="decimal" value={max} onChange={(e) => setMax(e.target.value)} />
              <SelectField label="Source" value={source} onChange={(e) => setSource(e.target.value)}
                options={[{ value: '', label: 'Non renseignée' }, ...(sources.data?.results ?? []).map((s) => ({ value: String(s.id), label: s.title }))]} />
            </div>
            <div className="flex justify-end"><Button type="submit" size="sm" icon={<Plus className="size-4" />}>Ajouter la contrainte</Button></div>
          </form>
        )}
      </div>
    </Card>
  )
}

export function ReferenceDetailPage() {
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
    a === null && b === null ? 'Non borné' : a !== null && b !== null && Number(a) === Number(b) ? `${a} ${unit}` : `${a ?? '…'} – ${b ?? '…'} ${unit}`

  return (
    <div className="space-y-6">
      <Link to="/references" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"><ArrowLeft className="size-4" /> Références</Link>
      <PageHeader title={r.name} description={<span className="flex flex-wrap items-center gap-2">Système {r.system_code} <ValidationBadge status={r.status} isDemo={r.is_demo} /></span>}
        actions={<WorkflowActions status={r.status} canSubmit={isReviewer} isReviewer={isReviewer} onAction={(a, c) => referenceService.act(r.id, a, c).then(refresh)} />} />
      {r.status === 'VALIDATED' && isReviewer && <Alert tone="info">Toute modification des besoins remettra cette référence en brouillon : elle devra être revalidée.</Alert>}
      {r.validation_comment && <Alert tone={r.status === 'REJECTED' ? 'warning' : 'info'} title="Commentaire de validation">{r.validation_comment}</Alert>}

      <Card>
        <DefinitionList items={[
          { label: 'Espèce', value: r.species_name },
          { label: 'Race', value: r.breed_name ?? 'Toutes' },
          { label: 'Catégorie', value: r.category_name ?? 'Toutes' },
          { label: 'Stade physiologique', value: r.physiological_stage_name ?? 'Tous' },
          { label: 'Objectif', value: r.objective_name ?? 'Tous' },
          { label: 'Poids', value: bound(r.weight_min_kg, r.weight_max_kg, 'kg') },
          { label: 'Âge', value: bound(r.age_min_months, r.age_max_months, 'mois') },
          { label: 'Ingestion de MS', value: bound(r.dm_intake_min_kg_day, r.dm_intake_max_kg_day, 'kg MS/j') },
          { label: 'Source', value: r.source?.title ?? 'Non renseignée (validation impossible)' },
          { label: 'Validée par', value: r.validated_by_email ? `${r.validated_by_email} le ${formatDate(r.validated_at)}` : '—' },
          { label: "Conditions d'application", value: r.application_conditions || '—' },
        ]} />
      </Card>

      <Card title="Besoins nutritionnels">
        <div className="space-y-4">
          {r.requirements.length === 0 ? <EmptyState title="Aucun besoin saisi">Une référence sans besoin ne peut pas être validée.</EmptyState> : (
            <div className="-mx-5 overflow-x-auto">
              <table className="w-full">
                <thead className="border-y border-slate-200 bg-slate-50"><tr>
                  <th className={th}>Nutriment</th><th className={th}>Expression</th><th className={th}>Minimum</th><th className={th}>Cible</th><th className={th}>Maximum</th><th className={th}>Unité</th>{isReviewer && <th className={th} />}
                </tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {r.requirements.map((q) => (
                    <tr key={q.id}>
                      <td className={td}><span className="font-medium">{q.nutrient_code}</span> <span className="text-xs text-slate-500">{q.nutrient_name}</span></td>
                      <td className={td}>{q.expression_label}</td>
                      <td className={td}>{q.min_value !== null ? formatNumber(q.min_value, 4) : '—'}</td>
                      <td className={td}>{q.target_value !== null ? formatNumber(q.target_value, 4) : '—'}</td>
                      <td className={td}>{q.max_value !== null ? formatNumber(q.max_value, 4) : '—'}</td>
                      <td className={td}>{q.unit_label}</td>
                      {isReviewer && <td className={`${td} text-right`}><button type="button" onClick={() => removeReq.mutate(q.id)} className="rounded-md p-2.5 text-slate-500 hover:text-red-600" aria-label={`Supprimer le besoin ${q.nutrient_code}`}><Trash2 className="size-4" /></button></td>}
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
