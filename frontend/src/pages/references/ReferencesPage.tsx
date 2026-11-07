import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { BookOpen, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, EmptyState } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { PageHeader, td, th } from '@/components/ui/Layout'
import { Modal } from '@/components/ui/Modal'
import { Pagination } from '@/components/ui/Pagination'
import { Spinner } from '@/components/ui/Spinner'
import { ValidationBadge } from '@/features/reference/Workflow'
import { useRoles } from '@/hooks/useRoles'
import { ApiError } from '@/services/api'
import { nomenclatureService } from '@/services/animals'
import { nutritionService, referenceService, sourceService } from '@/services/nutrition'
import { formatNumber } from '@/utils/format'

const select = 'rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm'

function range(min: string | null, max: string | null, unit: string) {
  if (min === null && max === null) return '—'
  return `${min !== null ? formatNumber(min, 3) : '…'} – ${max !== null ? formatNumber(max, 3) : '…'} ${unit}`
}

function NewReferenceModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const species = useQuery({ queryKey: ['species'], queryFn: nomenclatureService.species, staleTime: Infinity })
  const systems = useQuery({ queryKey: ['systems'], queryFn: nutritionService.systems, staleTime: Infinity })
  const sources = useQuery({ queryKey: ['sources'], queryFn: () => sourceService.list() })
  const objectives = useQuery({ queryKey: ['objectives'], queryFn: nutritionService.objectives, staleTime: Infinity })
  const [form, setForm] = useState({ name: '', species: '', system: '', category: '', physiological_stage: '', objective: '', source: '',
    weight_min_kg: '', weight_max_kg: '', age_min_months: '', age_max_months: '', dm_intake_min_kg_day: '', dm_intake_max_kg_day: '', application_conditions: '' })
  const sid = form.species ? Number(form.species) : undefined
  const categories = useQuery({ queryKey: ['categories', sid], queryFn: () => nomenclatureService.categories(sid), enabled: Boolean(sid) })
  const stages = useQuery({ queryKey: ['stages', sid], queryFn: () => nomenclatureService.stages(sid), enabled: Boolean(sid) })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const opts = (items: { id: number; name: string }[] | undefined, empty: string) => [{ value: '', label: empty }, ...(items ?? []).map((i) => ({ value: String(i.id), label: i.name }))]

  const submit = async () => {
    setError(null)
    if (!form.name.trim() || !form.species || !form.system) return setError("L'intitulé, l'espèce et le système nutritionnel sont obligatoires.")
    setBusy(true)
    try {
      const num = (v: string) => (v ? v.replace(',', '.') : null)
      const ref = await referenceService.create({
        name: form.name.trim(), species: Number(form.species), system: Number(form.system),
        category: form.category ? Number(form.category) : null, physiological_stage: form.physiological_stage ? Number(form.physiological_stage) : null,
        objective: form.objective ? Number(form.objective) : null, source: form.source ? Number(form.source) : null,
        weight_min_kg: num(form.weight_min_kg), weight_max_kg: num(form.weight_max_kg), age_min_months: num(form.age_min_months),
        age_max_months: num(form.age_max_months), dm_intake_min_kg_day: num(form.dm_intake_min_kg_day), dm_intake_max_kg_day: num(form.dm_intake_max_kg_day),
        application_conditions: form.application_conditions,
      })
      navigate(`/references/${ref.id}`)
    } catch (e) {
      setError(e instanceof ApiError ? Object.values(e.fieldErrors).flat().join(' ') || e.message : 'Création impossible.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open title="Nouvelle référence nutritionnelle" onClose={onClose}
      footer={<><Button variant="secondary" onClick={onClose}>Annuler</Button><Button onClick={submit} loading={busy}>Créer</Button></>}>
      <div className="max-h-[65vh] space-y-4 overflow-y-auto pr-1">
        {error && <Alert tone="error">{error}</Alert>}
        <TextField label="Intitulé" required value={form.name} onChange={set('name')} />
        <div className="grid gap-3 sm:grid-cols-2">
          <SelectField label="Espèce" required value={form.species} onChange={set('species')} options={opts(species.data, 'Choisir…')} />
          <SelectField label="Système nutritionnel" required value={form.system} onChange={set('system')}
            options={[{ value: '', label: 'Choisir…' }, ...(systems.data ?? []).map((s) => ({ value: String(s.id), label: `${s.name} ${s.version}` }))]} />
          <SelectField label="Catégorie" value={form.category} onChange={set('category')} options={opts(categories.data, 'Toutes')} />
          <SelectField label="Stade physiologique" value={form.physiological_stage} onChange={set('physiological_stage')} options={opts(stages.data, 'Tous')} />
          <SelectField label="Objectif" value={form.objective} onChange={set('objective')} options={opts(objectives.data, 'Tous')} />
          <SelectField label="Source" value={form.source} onChange={set('source')} options={opts(sources.data?.results.map((s) => ({ id: s.id, name: s.title })), 'À renseigner avant validation')} />
          <TextField label="Poids min. (kg)" inputMode="decimal" value={form.weight_min_kg} onChange={set('weight_min_kg')} />
          <TextField label="Poids max. (kg)" inputMode="decimal" value={form.weight_max_kg} onChange={set('weight_max_kg')} />
          <TextField label="Âge min. (mois)" inputMode="decimal" value={form.age_min_months} onChange={set('age_min_months')} />
          <TextField label="Âge max. (mois)" inputMode="decimal" value={form.age_max_months} onChange={set('age_max_months')} />
          <TextField label="Ingestion MS min. (kg/j)" inputMode="decimal" value={form.dm_intake_min_kg_day} onChange={set('dm_intake_min_kg_day')} />
          <TextField label="Ingestion MS max. (kg/j)" inputMode="decimal" value={form.dm_intake_max_kg_day} onChange={set('dm_intake_max_kg_day')} />
        </div>
        <TextField label="Conditions d'application" value={form.application_conditions} onChange={set('application_conditions')} />
        <p className="text-xs text-slate-500">Sans bornes d'ingestion de matière sèche, le moteur refusera de calculer avec cette référence.</p>
      </div>
    </Modal>
  )
}

export function ReferencesPage() {
  const { isReviewer } = useRoles()
  const [filters, setFilters] = useState<{ page: number; status?: string; system?: string }>({ page: 1 })
  const [creating, setCreating] = useState(false)
  const refs = useQuery({ queryKey: ['references', filters], queryFn: () => referenceService.list(filters), placeholderData: keepPreviousData })
  const systems = useQuery({ queryKey: ['systems'], queryFn: nutritionService.systems, staleTime: Infinity })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Références nutritionnelles"
        description="Besoins documentés par profil d'animal. Seules les références validées par un expert sont utilisées par le moteur de formulation."
        actions={isReviewer && <Button icon={<Plus className="size-4" />} onClick={() => setCreating(true)}>Nouvelle référence</Button>}
      />
      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2">
        <select aria-label="Système" className={select} value={filters.system ?? ''} onChange={(e) => setFilters({ ...filters, system: e.target.value, page: 1 })}>
          <option value="">Tous les systèmes</option>
          {systems.data?.map((s) => <option key={s.id} value={s.id}>{s.name} {s.version}</option>)}
        </select>
        <select aria-label="Statut" className={select} value={filters.status ?? ''} onChange={(e) => setFilters({ ...filters, status: e.target.value, page: 1 })}>
          <option value="">Tous statuts</option>
          <option value="VALIDATED">Validées</option>
          <option value="PENDING">En attente</option>
          <option value="DRAFT">Brouillons</option>
          <option value="REJECTED">Rejetées</option>
        </select>
      </div>
      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {refs.isPending ? <div className="p-6"><Spinner /></div> : refs.isError ? <div className="p-4"><Alert tone="error">{refs.error.message}</Alert></div> : refs.data.results.length === 0 ? (
          <EmptyState icon={<BookOpen className="size-10" />} title="Aucune référence nutritionnelle">
            Les références sont saisies par les experts à partir de sources identifiées, puis validées. Tant qu'aucune référence n'est validée,
            le moteur de formulation refuse de calculer.
          </EmptyState>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-slate-200 bg-slate-50"><tr>
                  <th className={th}>Référence</th><th className={th}>Profil</th><th className={th}>Poids</th><th className={th}>Ingestion MS</th><th className={th}>Besoins</th><th className={th}>Statut</th>
                </tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {refs.data.results.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/70">
                      <td className={td}><Link to={`/references/${r.id}`} className="font-medium text-brand-700 hover:underline">{r.name}</Link><p className="text-xs text-slate-500">{r.system_code} · {r.source?.title ?? 'sans source'}</p></td>
                      <td className={td}>{[r.species_name, r.category_name, r.physiological_stage_name, r.objective_name].filter(Boolean).join(' · ')}</td>
                      <td className={td}>{range(r.weight_min_kg, r.weight_max_kg, 'kg')}</td>
                      <td className={td}>{range(r.dm_intake_min_kg_day, r.dm_intake_max_kg_day, 'kg/j')}</td>
                      <td className={td}>{r.requirements.length}</td>
                      <td className={td}><ValidationBadge status={r.status} isDemo={r.is_demo} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={filters.page} pageSize={20} count={refs.data.count} onPageChange={(page) => setFilters({ ...filters, page })} />
          </>
        )}
      </section>
      {creating && <NewReferenceModal onClose={() => setCreating(false)} />}
    </div>
  )
}
