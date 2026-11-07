import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Alert as Notice, Card } from '@/components/ui/Feedback'
import { PageHeader } from '@/components/ui/Layout'
import { Pagination } from '@/components/ui/Pagination'
import { Spinner } from '@/components/ui/Spinner'
import { AlertList } from '@/features/alerts/AlertList'
import { useAuth } from '@/hooks/useAuth'
import { useFarm } from '@/hooks/useFarm'
import { alertService, type AlertFilters } from '@/services/alerts'

const select = 'rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm'

export function AlertsPage() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { selectedFarmId, canWrite, writableFarms } = useFarm()
  const [filters, setFilters] = useState<AlertFilters>({ page: 1 })
  const effective = { ...filters, farm: selectedFarmId }
  const alerts = useQuery({ queryKey: ['alerts', effective], queryFn: () => alertService.list(effective), placeholderData: keepPreviousData })

  const evaluate = useMutation({
    mutationFn: () => alertService.evaluate(selectedFarmId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const set = (key: keyof AlertFilters, value: string) => setFilters((f) => ({ ...f, [key]: value, page: 1 }))

  return (
    <div className="space-y-6">
      <PageHeader
        title="Alertes et rappels"
        description="Chaque alerte indique la règle appliquée et les valeurs qui l'ont déclenchée. Elle ne constitue jamais un diagnostic vétérinaire."
        actions={
          (writableFarms.length > 0 || user?.role === 'EXPERT') && (
            <Button variant="secondary" icon={<RefreshCw className="size-4" />} loading={evaluate.isPending} onClick={() => evaluate.mutate()}>
              Vérifier maintenant
            </Button>
          )
        }
      />
      {evaluate.isSuccess && (
        <Notice tone="success">
          Vérification terminée : {evaluate.data.created} nouvelle(s), {evaluate.data.resolved} résolue(s) automatiquement.
        </Notice>
      )}
      {evaluate.isError && <Notice tone="error">{evaluate.error.message}</Notice>}

      <div className="grid gap-3 rounded-md border border-slate-200 bg-white p-4 sm:grid-cols-3">
        <select aria-label="Statut" className={select} value={filters.status ?? ''} onChange={(e) => set('status', e.target.value)}>
          <option value="">Ouvertes</option>
          <option value="RESOLVED">Résolues</option>
          <option value="DISMISSED">Ignorées</option>
        </select>
        <select aria-label="Niveau" className={select} value={filters.severity ?? ''} onChange={(e) => set('severity', e.target.value)}>
          <option value="">Tous les niveaux</option>
          <option value="CRITICAL">Important</option>
          <option value="WARNING">Attention</option>
          <option value="INFO">Information</option>
        </select>
        <select aria-label="Type" className={select} value={filters.alert_type ?? ''} onChange={(e) => set('alert_type', e.target.value)}>
          <option value="">Tous les types</option>
          <option value="WEIGHING_REMINDER">Rappel de pesée</option>
          <option value="FOLLOW_UP_REMINDER">Rappel de suivi</option>
          <option value="MISSING_DATA">Information manquante</option>
          <option value="GROWTH_OUT_OF_RANGE">Croissance hors plage de suivi</option>
          <option value="FORMULA_TO_REVIEW">Formulation à vérifier</option>
          <option value="REFERENCE_TO_VALIDATE">Donnée de référence à valider</option>
        </select>
      </div>

      <Card>
        {alerts.isPending ? (
          <Spinner />
        ) : alerts.isError ? (
          <Notice tone="error">{alerts.error.message}</Notice>
        ) : (
          <>
            <AlertList
              alerts={alerts.data.results}
              canAct={(a) => (a.farm ? canWrite(a.farm) : true)}
              emptyTitle={filters.status ? 'Aucune alerte dans cette catégorie' : 'Aucune alerte ouverte'}
            />
            <div className="-mx-5 -mb-5 mt-4">
              <Pagination page={filters.page ?? 1} pageSize={20} count={alerts.data.count} onPageChange={(page) => setFilters((f) => ({ ...f, page }))} />
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
