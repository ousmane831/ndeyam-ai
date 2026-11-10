import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, Plus, Square, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, Card, EmptyState } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { PageHeader, StatCard, Tabs, td, th } from '@/components/ui/Layout'
import { ConfirmDialog, Modal } from '@/components/ui/Modal'
import { Pagination } from '@/components/ui/Pagination'
import { Spinner } from '@/components/ui/Spinner'
import { validateFeeding } from '@/features/feeding/feedingForm'
import { useFarm } from '@/hooks/useFarm'
import { ApiError } from '@/services/api'
import { animalService, groupService } from '@/services/animals'
import { feedingService, type RationSummary, type RecordFilters } from '@/services/feeding'
import { canCreateRation } from '@/features/formulation/rationRules'
import { formulaService } from '@/services/formulas'
import { formatDate, formatMoney, formatNumber, todayIso } from '@/utils/format'

type TabId = 'rations' | 'distributions'
const errorText = (e: unknown, fallback: string) => (e instanceof ApiError ? Object.values(e.fieldErrors).flat().join(' ') || e.message : e instanceof Error ? e.message : fallback)
const dec = (v: string) => (v.trim() ? v.trim().replace(',', '.') : null)

function RationModal({ farmId, initialFormula, onClose }: { farmId: number; initialFormula?: string; onClose: () => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const formulas = useQuery({ queryKey: ['formulas-all', farmId], queryFn: () => formulaService.all(farmId) })
  const animals = useQuery({ queryKey: ['animal-options', farmId], queryFn: () => animalService.options(farmId) })
  const groups = useQuery({ queryKey: ['groups', farmId], queryFn: () => groupService.list(farmId) })
  const [f, setF] = useState({ name: '', formula: initialFormula ?? '', target: 'group', animal: '', group: '', start: todayIso(), planned: '' })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((s) => ({ ...s, [k]: e.target.value }))
  // Une estimation non vérifiée ne nourrit jamais un animal : seules les formules autorisées sont proposées.
  const usable = (formulas.data ?? []).filter((x) => x.items.length > 0 && canCreateRation(x))
  const waiting = (formulas.data ?? []).filter((x) => x.items.length > 0 && !canCreateRation(x)).length
  const chosen = usable.find((x) => String(x.id) === f.formula)

  const submit = async () => {
    setError(null)
    if (!f.name.trim() || !f.formula) return setError(t('Le nom et la formule sont obligatoires.'))
    if (f.target === 'animal' ? !f.animal : !f.group) return setError(f.target === 'animal' ? t('Choisissez un animal.') : t('Choisissez un lot.'))
    setBusy(true)
    try {
      await feedingService.createRation({
        farm: farmId, name: f.name.trim(), formula: Number(f.formula), start_date: f.start,
        animal: f.target === 'animal' ? Number(f.animal) : null, group: f.target === 'group' ? Number(f.group) : null,
        planned_as_fed_kg_per_animal_day: dec(f.planned),
      })
      await queryClient.invalidateQueries({ queryKey: ['rations'] })
      onClose()
    } catch (e) {
      setError(errorText(e, t('Action impossible.')))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open title={t('Nouvelle ration')} onClose={onClose} footer={<><Button variant="secondary" onClick={onClose}>{t('Annuler')}</Button><Button onClick={submit} loading={busy}>{t('Créer')}</Button></>}>
      <div className="space-y-4">
        {error && <Alert tone="error">{error}</Alert>}
        <TextField label={t('Nom de la ration')} required value={f.name} onChange={set('name')} />
        <SelectField label={t('Formule')} required value={f.formula} onChange={set('formula')}
          options={[{ value: '', label: t('Choisir…') }, ...usable.map((x) => ({ value: String(x.id), label: `${x.name} — ${t(x.status_label)}` }))]} />
        {chosen?.mode === 'MANUAL' && chosen.status !== 'VALIDATED' && <Alert tone="info">{t("Ration saisie : ses apports n'ont pas été vérifiés par un expert.")}</Alert>}
        {waiting > 0 && <p className="text-sm text-slate-500">{t('{{count}} formule(s) calculée(s) en attente de validation par un expert ne sont pas proposées.', { count: waiting })}</p>}
        <div className="flex gap-4 text-sm">
          <label className="inline-flex items-center gap-2"><input type="radio" checked={f.target === 'group'} onChange={() => setF({ ...f, target: 'group' })} className="accent-brand-600" /> {t('Un lot')}</label>
          <label className="inline-flex items-center gap-2"><input type="radio" checked={f.target === 'animal'} onChange={() => setF({ ...f, target: 'animal' })} className="accent-brand-600" /> {t('Un animal')}</label>
        </div>
        {f.target === 'group' ? (
          <SelectField label={t('Lot')} value={f.group} onChange={set('group')} options={[{ value: '', label: t('Choisir…') }, ...(groups.data?.results ?? []).map((g) => ({ value: String(g.id), label: g.name }))]} />
        ) : (
          <SelectField label={t('Animal')} value={f.animal} onChange={set('animal')} options={[{ value: '', label: t('Choisir…') }, ...(animals.data ?? []).map((a) => ({ value: String(a.id), label: a.tag_number }))]} />
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          <TextField label={t('Date de début')} type="date" value={f.start} onChange={set('start')} />
          <TextField label={t('Quantité prévue (kg brut / animal / j)')} inputMode="decimal" value={f.planned} onChange={set('planned')}
            placeholder={chosen?.as_fed_kg_day ? formatNumber(chosen.as_fed_kg_day, 3) : ''} />
        </div>
      </div>
    </Modal>
  )
}

function RecordModal({ farmId, rations, onClose }: { farmId: number; rations: RationSummary[]; onClose: () => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [ration, setRation] = useState(rations.find((r) => r.status === 'ACTIVE')?.id.toString() ?? '')
  const [v, setV] = useState({ date: todayIso(), distributed: '', consumed: '', refused: '', heads: '', notes: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const selected = rations.find((r) => String(r.id) === ration)
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV((s) => ({ ...s, [k]: e.target.value }))

  const submit = async () => {
    setError(null)
    if (!selected) return setError(t('Choisissez la ration distribuée.'))
    const found = validateFeeding({ ...v, targetIsGroup: selected.group !== null }, todayIso())
    setErrors(found)
    if (Object.keys(found).length) return
    setBusy(true)
    try {
      await feedingService.createRecord({
        farm: farmId, ration: selected.id, fed_on: v.date, quantity_distributed_kg: dec(v.distributed),
        quantity_consumed_kg: dec(v.consumed), quantity_refused_kg: dec(v.refused),
        number_of_animals: selected.group !== null ? Number(v.heads) : null, notes: v.notes,
      })
      for (const k of ['feeding-records', 'feeding-summary', 'dashboard', 'alerts']) queryClient.invalidateQueries({ queryKey: [k] })
      onClose()
    } catch (e) {
      setError(errorText(e, t('Action impossible.')))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open title={t('Enregistrer une distribution')} onClose={onClose} footer={<><Button variant="secondary" onClick={onClose}>{t('Annuler')}</Button><Button onClick={submit} loading={busy}>{t('Enregistrer')}</Button></>}>
      <div className="space-y-4">
        {error && <Alert tone="error">{error}</Alert>}
        <SelectField label={t('Ration')} value={ration} onChange={(e) => setRation(e.target.value)}
          options={[{ value: '', label: t('Choisir…') }, ...rations.map((r) => ({ value: String(r.id), label: `${r.name} — ${t(r.target_label)}${r.status === 'ENDED' ? t(' (terminée)') : ''}` }))]} />
        <div className="grid gap-3 sm:grid-cols-2">
          <TextField label={t('Date')} type="date" max={todayIso()} value={v.date} onChange={set('date')} error={errors.date} />
          {selected?.group !== null && selected && <TextField label={t('Animaux nourris')} inputMode="numeric" value={v.heads} onChange={set('heads')} error={errors.heads} />}
          <TextField label={t('Quantité distribuée (kg brut)')} inputMode="decimal" required value={v.distributed} onChange={set('distributed')} error={errors.distributed} />
          <TextField label={t('Refus pesés (kg brut)')} inputMode="decimal" value={v.refused} onChange={set('refused')} error={errors.refused} />
          <TextField label={t('Consommée mesurée (kg brut)')} inputMode="decimal" value={v.consumed} onChange={set('consumed')} error={errors.consumed}
            hint={t("À renseigner uniquement si elle a été mesurée : elle n'est jamais déduite.")} />
          <TextField label={t('Notes')} value={v.notes} onChange={set('notes')} />
        </div>
        <p className="text-xs text-slate-500">{t('La quantité calculée (prévue par la ration) et le coût estimé sont déterminés automatiquement.')}</p>
      </div>
    </Modal>
  )
}

function RationsTab({ farmId, writable, initialFormula }: { farmId: number | null; writable: boolean; initialFormula?: string }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [status, setStatus] = useState('ACTIVE')
  const [creating, setCreating] = useState(Boolean(initialFormula))
  const [ending, setEnding] = useState<RationSummary | null>(null)
  const [endDate, setEndDate] = useState(todayIso())
  const [toDelete, setToDelete] = useState<RationSummary | null>(null)
  const rations = useQuery({ queryKey: ['rations', farmId, status], queryFn: () => feedingService.rations({ farm: farmId, status }) })
  const end = useMutation({ mutationFn: (r: RationSummary) => feedingService.endRation(r.id, endDate), onSuccess: () => { setEnding(null); queryClient.invalidateQueries({ queryKey: ['rations'] }) } })
  const removal = useMutation({ mutationFn: (r: RationSummary) => feedingService.removeRation(r.id), onSuccess: () => { setToDelete(null); queryClient.invalidateQueries({ queryKey: ['rations'] }) } })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <select aria-label={t('Statut des rations')} value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
          <option value="ACTIVE">{t('En cours')}</option><option value="ENDED">{t('Terminées')}</option><option value="">{t('Toutes')}</option>
        </select>
        {writable && farmId && <Button icon={<Plus className="size-4" />} onClick={() => setCreating(true)}>{t('Nouvelle ration')}</Button>}
      </div>
      <Card>
        {rations.isPending ? <Spinner /> : rations.isError ? <Alert tone="error">{rations.error.message}</Alert> : rations.data.results.length === 0 ? (
          <EmptyState title={t('Aucune ration')}>{t("Créez une ration à partir d'une formule calculée ou saisie, puis associez-la à un lot ou à un animal.")}</EmptyState>
        ) : (
          <ul className="divide-y divide-slate-100">
            {rations.data.results.map((r) => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <div>
                  <p className="font-medium text-slate-800">{r.name} {r.is_demo && <Badge tone="demo">DEMO</Badge>}</p>
                  <p className="text-sm text-slate-500">
                    {t(r.target_label)} · {t('formule')} <Link to={`/formulation/${r.formula}`} className="text-brand-700 hover:underline">{r.formula_name}</Link> ({t(r.formula_status_label)}) ·{' '}
                    {r.end_date
                      ? t('du {{start}} au {{end}}', { start: formatDate(r.start_date), end: formatDate(r.end_date) })
                      : t('du {{start}}', { start: formatDate(r.start_date) })}
                    {r.planned_as_fed_kg_per_animal_day && t(' · {{quantity}} kg brut/animal/j', { quantity: formatNumber(r.planned_as_fed_kg_per_animal_day, 3) })}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={r.status === 'ACTIVE' ? 'brand' : 'neutral'}>{t(r.status_label)}</Badge>
                  {writable && r.status === 'ACTIVE' && <Button size="sm" variant="secondary" icon={<Square className="size-3.5" />} onClick={() => setEnding(r)}>{t('Terminer')}</Button>}
                  {writable && <button type="button" onClick={() => setToDelete(r)} className="rounded-md p-2.5 text-slate-500 hover:text-red-600" aria-label={t('Supprimer {{name}}', { name: r.name })}><Trash2 className="size-4" /></button>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
      {creating && farmId && <RationModal farmId={farmId} initialFormula={initialFormula} onClose={() => setCreating(false)} />}
      <Modal open={ending !== null} title={t('Terminer « {{name}} »', { name: ending?.name })} onClose={() => setEnding(null)}
        footer={<><Button variant="secondary" onClick={() => setEnding(null)}>{t('Annuler')}</Button><Button loading={end.isPending} onClick={() => ending && end.mutate(ending)}>{t('Terminer')}</Button></>}>
        {end.isError && <Alert tone="error">{end.error.message}</Alert>}
        <TextField label={t('Date de fin')} type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
      </Modal>
      <ConfirmDialog open={toDelete !== null} title={t('Supprimer cette ration ?')} danger confirmLabel={t('Supprimer')} loading={removal.isPending}
        message={<>{t('Les distributions déjà enregistrées sont conservées sans lien avec la ration.')}{removal.isError && <span className="mt-2 block text-red-600">{removal.error.message}</span>}</>}
        onConfirm={() => toDelete && removal.mutate(toDelete)} onCancel={() => setToDelete(null)} />
    </div>
  )
}

function DistributionsTab({ farmId, writable }: { farmId: number | null; writable: boolean }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState<RecordFilters>({ page: 1 })
  const [recording, setRecording] = useState(false)
  const effective = { ...filters, farm: farmId }
  const records = useQuery({ queryKey: ['feeding-records', effective], queryFn: () => feedingService.records(effective), placeholderData: keepPreviousData })
  const summary = useQuery({ queryKey: ['feeding-summary', effective], queryFn: () => feedingService.summary(effective) })
  const rations = useQuery({ queryKey: ['rations', farmId, ''], queryFn: () => feedingService.rations({ farm: farmId }) })
  const removal = useMutation({ mutationFn: feedingService.removeRecord, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['feeding-records'] }); queryClient.invalidateQueries({ queryKey: ['feeding-summary'] }) } })
  const s = summary.data

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap gap-3">
          <TextField label={t('Du')} type="date" value={filters.fed_on__gte ?? ''} onChange={(e) => setFilters({ ...filters, fed_on__gte: e.target.value, page: 1 })} />
          <TextField label={t('Au')} type="date" value={filters.fed_on__lte ?? ''} onChange={(e) => setFilters({ ...filters, fed_on__lte: e.target.value, page: 1 })} />
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" icon={<Download className="size-4" />} onClick={() => feedingService.exportCsv(effective)}>{t('Exporter')}</Button>
          {writable && farmId && <Button icon={<Plus className="size-4" />} disabled={!rations.data?.results.length} onClick={() => setRecording(true)}>{t('Enregistrer une distribution')}</Button>}
        </div>
      </div>
      {s && (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard label={t('Distribué')} value={s.distributed_kg ? `${formatNumber(s.distributed_kg)} kg` : '—'} hint={t('{{count}} distribution(s)', { count: s.records })} />
          <StatCard label={t('Consommé mesuré')} value={s.consumed_kg ? `${formatNumber(s.consumed_kg)} kg` : '—'} hint={t('Mesuré sur {{count}} distribution(s)', { count: s.records_with_measured_consumption })} />
          <StatCard label={t('Coût estimé')} value={formatMoney(s.estimated_cost)} hint={s.records_without_cost ? t('{{count}} distribution(s) sans coût connu', { count: s.records_without_cost }) : undefined} />
        </div>
      )}
      <section className="overflow-hidden rounded-md border border-slate-200 bg-white">
        {records.isPending ? <div className="p-6"><Spinner /></div> : records.isError ? <div className="p-4"><Alert tone="error">{records.error.message}</Alert></div> : records.data.results.length === 0 ? (
          <EmptyState title={t('Aucune distribution enregistrée')} />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-slate-200 bg-slate-50"><tr>
                  <th className={th}>{t('Date')}</th><th className={th}>{t('Ration')}</th><th className={th}>{t('Cible')}</th><th className={th}>{t('Calculée')}</th><th className={th}>{t('Distribuée')}</th><th className={th}>{t('Consommée')}</th><th className={th}>{t('Coût estimé')}</th>{writable && <th className={th} />}
                </tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {records.data.results.map((r) => (
                    <tr key={r.id}>
                      <td className={td}>{formatDate(r.fed_on)}</td>
                      <td className={td}>{r.ration_name ?? '—'}</td>
                      <td className={td}>{t(r.target_label)}{r.number_of_animals ? ` (${r.number_of_animals})` : ''}</td>
                      <td className={td}>{r.quantity_calculated_kg ? `${formatNumber(r.quantity_calculated_kg, 3)} kg` : '—'}</td>
                      <td className={td}>{formatNumber(r.quantity_distributed_kg, 3)} kg</td>
                      <td className={td}>{r.quantity_consumed_kg ? `${formatNumber(r.quantity_consumed_kg, 3)} kg` : t('Non mesurée')}</td>
                      <td className={td}>{formatMoney(r.estimated_cost, r.currency)}</td>
                      {writable && <td className={`${td} text-right`}><button type="button" onClick={() => removal.mutate(r.id)} className="rounded-md p-2.5 text-slate-500 hover:text-red-600" aria-label={t('Supprimer la distribution')}><Trash2 className="size-4" /></button></td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={filters.page ?? 1} pageSize={20} count={records.data.count} onPageChange={(page) => setFilters({ ...filters, page })} />
          </>
        )}
      </section>
      {s?.note && <p className="text-xs text-slate-500">{s.note}</p>}
      {recording && farmId && rations.data && <RecordModal farmId={farmId} rations={rations.data.results} onClose={() => setRecording(false)} />}
    </div>
  )
}

export function RationsPage() {
  const { t } = useTranslation()
  const [params, setParams] = useSearchParams()
  const { selectedFarmId, defaultWritableFarmId, canWrite } = useFarm()
  const farmId = selectedFarmId ?? defaultWritableFarmId
  const tab = (params.get('onglet') as TabId) || 'rations'
  const writable = farmId !== null && canWrite(farmId)
  return (
    <div className="space-y-6">
      <PageHeader title={t('Historique des rations')} description={t("Rations en cours et distributions. Les quantités calculée, distribuée et consommée sont distinguées ; la consommation n'est jamais supposée.")} />
      <Tabs<TabId> active={tab} onChange={(id) => setParams({ onglet: id })} tabs={[{ id: 'rations', label: t('Rations') }, { id: 'distributions', label: t('Distributions') }]} />
      {tab === 'rations' ? <RationsTab farmId={farmId} writable={writable} initialFormula={params.get('formule') ?? undefined} /> : <DistributionsTab farmId={farmId} writable={writable} />}
    </div>
  )
}
