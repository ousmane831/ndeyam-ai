import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { GitCompare } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, EmptyState } from '@/components/ui/Feedback'
import { FormulaStatus } from '@/features/formulation/FormulaStatus'
import { PageHeader, Tabs, td, th } from '@/components/ui/Layout'
import { Pagination } from '@/components/ui/Pagination'
import { Spinner } from '@/components/ui/Spinner'
import { CalculationForm } from '@/features/formulation/CalculationForm'
import { ManualForm } from '@/features/formulation/ManualForm'
import { useFarm } from '@/hooks/useFarm'
import { formulaService } from '@/services/formulas'
import { formatDateTime, formatMoney } from '@/utils/format'

type TabId = 'calcul' | 'manuel' | 'formules'


function FormulaList() {
  const navigate = useNavigate()
  const { selectedFarmId } = useFarm()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [selected, setSelected] = useState<number[]>([])
  const list = useQuery({ queryKey: ['formulas', selectedFarmId, page, status], queryFn: () => formulaService.list({ farm: selectedFarmId, page, status }), placeholderData: keepPreviousData })
  const toggle = (id: number) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length < 5 ? [...s, id] : s))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <select aria-label="Statut" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm">
          <option value="">Tous statuts</option>
          <option value="ESTIMATED">Estimations</option>
          <option value="PENDING_REVIEW">En attente de vérification</option>
          <option value="VALIDATED">Validées</option>
          <option value="INFEASIBLE">Impossibles</option>
          <option value="REFUSED">Refusées</option>
          <option value="DRAFT">Saisies (brouillon)</option>
        </select>
        <Button variant="secondary" icon={<GitCompare className="size-4" />} disabled={selected.length < 2}
          onClick={() => navigate(`/formulation/comparer?ids=${selected.join(',')}`)}>Comparer ({selected.length})</Button>
      </div>
      <section className="overflow-hidden rounded-md border border-slate-200 bg-white">
        {list.isPending ? <div className="p-6"><Spinner /></div> : list.isError ? <div className="p-4"><Alert tone="error">{list.error.message}</Alert></div> : list.data.results.length === 0 ? (
          <EmptyState title="Aucune formule enregistrée">Calculez une formule ou saisissez la ration que vous utilisez.</EmptyState>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-slate-200 bg-slate-50"><tr><th className={th}>Comparer</th><th className={th}>Formule</th><th className={th}>Mode</th><th className={th}>Statut</th><th className={th}>Coût / animal / j</th><th className={th}>Date</th></tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {list.data.results.map((f) => (
                    <tr key={f.id} className="hover:bg-slate-50/70">
                      <td className={td}><input type="checkbox" aria-label={`Comparer ${f.name}`} checked={selected.includes(f.id)} onChange={() => toggle(f.id)} className="size-5 accent-brand-700" /></td>
                      <td className={td}><Link to={`/formulation/${f.id}`} className="font-medium text-brand-700 hover:underline">{f.name}</Link></td>
                      <td className={td}>{f.mode_label}</td>
                      <td className={td}><FormulaStatus status={f.status} label={f.status_label} isDemo={f.is_demo} /></td>
                      <td className={td}>{formatMoney(f.cost_per_day, f.currency)}</td>
                      <td className={td}>{formatDateTime(f.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={20} count={list.data.count} onPageChange={setPage} />
          </>
        )}
      </section>
    </div>
  )
}

export function FormulationPage() {
  const [params, setParams] = useSearchParams()
  const tab = (params.get('onglet') as TabId) || 'calcul'
  return (
    <div className="space-y-6">
      <PageHeader title="Formulation des aliments"
        description="Le moteur calcule une ration à partir des seules données validées (références, compositions, contraintes). Le résultat est une estimation mathématique jusqu'à la vérification d'un expert." />
      <Tabs<TabId> active={tab} onChange={(id) => setParams({ onglet: id })}
        tabs={[{ id: 'calcul', label: 'Calcul optimisé' }, { id: 'manuel', label: 'Ration saisie' }, { id: 'formules', label: 'Formules enregistrées' }]} />
      {tab === 'calcul' && <CalculationForm />}
      {tab === 'manuel' && <ManualForm />}
      {tab === 'formules' && <FormulaList />}
    </div>
  )
}
