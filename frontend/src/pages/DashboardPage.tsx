import { useQuery } from '@tanstack/react-query'
import { Bell, Layers, PawPrint, Scale, Wallet } from 'lucide-react'
import { Link } from 'react-router'
import { DistributionChart, WeightTrendChart } from '@/components/LazyChart'
import { Alert, Badge, Card, EmptyState } from '@/components/ui/Feedback'
import { PageHeader, StatCard } from '@/components/ui/Layout'
import { Spinner } from '@/components/ui/Spinner'
import { useAuth } from '@/hooks/useAuth'
import { useFarm } from '@/hooks/useFarm'
import { dashboardService } from '@/services/alerts'
import { fetchHealth } from '@/services/system'
import { formatDate, formatDateTime, formatMoney, formatNumber } from '@/utils/format'

/** Tableau de bord : uniquement des données enregistrées, avec des états vides explicites. */
export function DashboardPage() {
  const { user } = useAuth()
  const { selectedFarmId, farms } = useFarm()
  const dashboard = useQuery({ queryKey: ['dashboard', selectedFarmId], queryFn: () => dashboardService.get(selectedFarmId) })
  const health = useQuery({ queryKey: ['health'], queryFn: fetchHealth, retry: false })

  const scope = selectedFarmId ? farms.find((f) => f.id === selectedFarmId)?.name : farms.length > 1 ? 'toutes vos exploitations' : farms[0]?.name

  if (dashboard.isPending) return <Spinner />
  if (dashboard.isError) return <Alert tone="error">{dashboard.error.message}</Alert>
  const d = dashboard.data

  if (d.farms_count === 0) {
    return (
      <div className="space-y-6">
        <PageHeader title={`Bonjour ${user?.first_name ?? ''}`} />
        <Card>
          <EmptyState icon={<PawPrint className="size-10" />} title="Aucune exploitation accessible">
            {user?.role === 'EXPERT'
              ? "Aucun éleveur ne vous a encore invité à consulter son exploitation."
              : (
                <>
                  Créez votre exploitation depuis les <Link to="/parametres" className="text-brand-700 hover:underline">paramètres</Link>.
                </>
              )}
          </EmptyState>
        </Card>
      </div>
    )
  }

  const cost = d.feeding_cost
  return (
    <div className="space-y-6">
      <PageHeader title={`Bonjour ${user?.first_name ?? ''}`} description={scope ? `Vue d'ensemble : ${scope}.` : undefined} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Animaux présents" value={d.animals.total} icon={<PawPrint className="size-5" />}
          hint={d.animals.total ? `${d.animals.by_sex.F} femelle(s), ${d.animals.by_sex.M} mâle(s)` : 'Aucun animal enregistré'} />
        <StatCard label="Lots actifs" value={d.groups_count} icon={<Layers className="size-5" />} />
        <StatCard label="Pesées (30 derniers jours)" value={d.weighings.last_30_days} icon={<Scale className="size-5" />}
          hint={d.weighings.never_weighed ? `${d.weighings.never_weighed} animal(aux) jamais pesé(s)` : undefined} />
        <StatCard
          label="Coût d'alimentation estimé (30 j)"
          value={cost.estimated_cost !== null ? formatMoney(cost.estimated_cost, cost.currency) : '—'}
          icon={<Wallet className="size-5" />}
          hint={
            cost.records === 0
              ? 'Aucune distribution enregistrée'
              : cost.records_without_cost
                ? `${cost.records_without_cost} distribution(s) sur ${cost.records} sans coût connu`
                : `Sur ${cost.records} distribution(s)`
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Répartition des animaux">
          {d.animals.total === 0 ? (
            <EmptyState title="Aucun animal">
              <Link to="/animaux/nouveau" className="text-brand-700 hover:underline">Ajouter un animal</Link>
            </EmptyState>
          ) : (
            <>
              <DistributionChart data={d.animals.by_category} />
              <p className="mt-2 text-xs text-slate-500">
                Par catégorie · espèces : {d.animals.by_species.map((s) => `${s.name} (${s.count})`).join(', ')}
              </p>
            </>
          )}
        </Card>
        <Card title="Évolution du poids">
          {d.weight_trend.points.length === 0 ? (
            <EmptyState title="Aucune pesée sur les six derniers mois" />
          ) : (
            <>
              <WeightTrendChart points={d.weight_trend.points} />
              <p className="mt-2 text-xs text-slate-500">{d.weight_trend.note}</p>
            </>
          )}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Dernières pesées" actions={<Link to="/suivi-croissance" className="text-sm font-medium text-brand-700 hover:underline">Suivi</Link>}>
          {d.weighings.latest.length === 0 ? (
            <EmptyState title="Aucune pesée" />
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {d.weighings.latest.map((w) => (
                <li key={w.id} className="flex justify-between gap-2 py-2 first:pt-0">
                  <Link to={`/animaux/${w.animal_id}`} className="truncate text-brand-700 hover:underline">{w.animal}</Link>
                  <span className="shrink-0 text-slate-600">{formatNumber(w.weight_kg)} kg · {formatDate(w.weighed_on)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Rations en cours">
          {d.rations.active_count === 0 ? (
            <EmptyState title="Aucune ration en cours" />
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {d.rations.active.map((r) => (
                <li key={r.id} className="py-2 first:pt-0">
                  <p className="font-medium text-slate-800">{r.name}</p>
                  <p className="text-xs text-slate-500">{r.target} · depuis le {formatDate(r.start_date)} · {r.formula_status}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Alertes" actions={<Link to="/alertes" className="text-sm font-medium text-brand-700 hover:underline">Tout voir</Link>}>
          {d.alerts.open === 0 ? (
            <EmptyState icon={<Bell className="size-8" />} title="Aucune alerte ouverte" />
          ) : (
            <ul className="space-y-2 text-sm">
              {d.alerts.latest.map((a) => (
                <li key={a.id} className="flex items-start gap-2">
                  <Badge tone={a.severity === 'INFO' ? 'neutral' : a.severity === 'WARNING' ? 'warning' : 'danger'}>
                    {a.severity === 'INFO' ? 'Info' : a.severity === 'WARNING' ? 'Attention' : 'Important'}
                  </Badge>
                  <span className="text-slate-700">{a.title}</span>
                </li>
              ))}
              {d.alerts.open > d.alerts.latest.length && <li className="text-xs text-slate-500">… et {d.alerts.open - d.alerts.latest.length} autre(s).</li>}
            </ul>
          )}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Activités récentes" className="lg:col-span-2">
          {d.recent_activity.length === 0 ? (
            <EmptyState title="Aucune activité enregistrée" />
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {d.recent_activity.map((e) => (
                <li key={e.id} className="flex flex-wrap justify-between gap-2 py-2 first:pt-0">
                  <span className="text-slate-700">
                    <span className="font-medium">{e.label}</span>
                    {e.object && ` — ${e.object}`}
                  </span>
                  <span className="text-xs text-slate-500">{e.actor ?? '—'} · {formatDateTime(e.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Services">
          {health.isPending ? (
            <Spinner />
          ) : health.isError ? (
            <Alert tone="error">{health.error.message}</Alert>
          ) : (
            <ul className="space-y-2 text-sm text-slate-600">
              <li>Base de données : {health.data.database.connected ? 'connectée' : 'inaccessible'}</li>
              <li>
                Assistant IA :{' '}
                {health.data.assistant.configured ? `configuré (${health.data.assistant.provider})` : 'non configuré — les autres modules restent utilisables'}
              </li>
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}
