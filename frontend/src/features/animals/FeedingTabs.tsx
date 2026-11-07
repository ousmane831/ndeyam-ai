import { useQuery } from '@tanstack/react-query'
import { Wheat } from 'lucide-react'
import { Alert, Badge, Card, EmptyState } from '@/components/ui/Feedback'
import { td, th } from '@/components/ui/Layout'
import { Spinner } from '@/components/ui/Spinner'
import { feedingService } from '@/services/feeding'
import { formatDate, formatMoney, formatNumber } from '@/utils/format'

export function RationsTab({ animalId }: { animalId: number }) {
  const rations = useQuery({ queryKey: ['rations', { animal: animalId }], queryFn: () => feedingService.rations({ animal: animalId }) })
  return (
    <Card title="Rations de l'animal">
      {rations.isPending ? (
        <Spinner />
      ) : rations.isError ? (
        <Alert tone="error">{rations.error.message}</Alert>
      ) : rations.data.results.length === 0 ? (
        <EmptyState icon={<Wheat className="size-10" />} title="Aucune ration associée à cet animal" />
      ) : (
        <ul className="divide-y divide-slate-100">
          {rations.data.results.map((r) => (
            <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 py-3 first:pt-0 last:pb-0">
              <div>
                <p className="font-medium text-slate-800">{r.name}</p>
                <p className="text-sm text-slate-500">
                  Formule « {r.formula_name} » · du {formatDate(r.start_date)} {r.end_date ? `au ${formatDate(r.end_date)}` : '(en cours)'}
                  {r.planned_as_fed_kg_per_animal_day && ` · ${formatNumber(r.planned_as_fed_kg_per_animal_day, 3)} kg brut/j prévus`}
                </p>
              </div>
              <div className="flex gap-2">
                <Badge tone={r.status === 'ACTIVE' ? 'brand' : 'neutral'}>{r.status_label}</Badge>
                <Badge>{r.formula_status_label}</Badge>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

export function FeedingHistoryTab({ animalId }: { animalId: number }) {
  const records = useQuery({ queryKey: ['feeding-records', { animal: animalId }], queryFn: () => feedingService.records({ animal: animalId }) })
  return (
    <Card title="Historique alimentaire">
      {records.isPending ? (
        <Spinner />
      ) : records.isError ? (
        <Alert tone="error">{records.error.message}</Alert>
      ) : records.data.results.length === 0 ? (
        <EmptyState icon={<Wheat className="size-10" />} title="Aucune distribution enregistrée pour cet animal" />
      ) : (
        <div className="-mx-5 overflow-x-auto">
          <table className="w-full">
            <thead className="border-y border-slate-200 bg-slate-50">
              <tr>
                <th className={th}>Date</th>
                <th className={th}>Ration</th>
                <th className={th}>Calculée</th>
                <th className={th}>Distribuée</th>
                <th className={th}>Consommée (mesurée)</th>
                <th className={th}>Coût estimé</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {records.data.results.map((r) => (
                <tr key={r.id}>
                  <td className={td}>{formatDate(r.fed_on)}</td>
                  <td className={td}>{r.ration_name ?? '—'}</td>
                  <td className={td}>{r.quantity_calculated_kg ? `${formatNumber(r.quantity_calculated_kg, 3)} kg` : '—'}</td>
                  <td className={td}>{formatNumber(r.quantity_distributed_kg, 3)} kg</td>
                  <td className={td}>{r.quantity_consumed_kg ? `${formatNumber(r.quantity_consumed_kg, 3)} kg` : 'Non mesurée'}</td>
                  <td className={td}>{formatMoney(r.estimated_cost, r.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
