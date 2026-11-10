import { useQuery } from '@tanstack/react-query'
import { Layers, PawPrint, Scale, Wallet } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { WeightTrendChart } from '@/components/LazyChart'
import { Alert, AnimalTag, Card, EmptyState } from '@/components/ui/Feedback'
import { PageHeader, StatCard } from '@/components/ui/Layout'
import { Spinner } from '@/components/ui/Spinner'
import { TodayTasks } from '@/features/dashboard/TodayTasks'
import { useAuth } from '@/hooks/useAuth'
import { useFarm } from '@/hooks/useFarm'
import { dashboardService } from '@/services/alerts'
import { fetchHealth } from '@/services/system'
import { formatDate, formatDateTime, formatMoney, formatNumber } from '@/utils/format'

/** Tableau de bord : uniquement des données enregistrées, avec des états vides explicites. */
export function DashboardPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { selectedFarmId, farms } = useFarm()
  const dashboard = useQuery({ queryKey: ['dashboard', selectedFarmId], queryFn: () => dashboardService.get(selectedFarmId) })
  const isAdmin = Boolean(user?.is_platform_admin)
  // État des services : information d'administration, inutile à un éleveur.
  const health = useQuery({ queryKey: ['health'], queryFn: fetchHealth, retry: false, enabled: isAdmin })

  const scope = selectedFarmId ? farms.find((f) => f.id === selectedFarmId)?.name : farms.length > 1 ? t('toutes vos exploitations') : farms[0]?.name

  if (dashboard.isPending) return <Spinner />
  if (dashboard.isError) return <Alert tone="error">{dashboard.error.message}</Alert>
  const d = dashboard.data

  if (d.farms_count === 0) {
    return (
      <div className="space-y-6">
        <PageHeader title={t('Bonjour {{name}}', { name: user?.first_name ?? '' })} />
        <Card>
          <EmptyState icon={<PawPrint className="size-10" />} title={t('Aucune exploitation accessible')}>
            {user?.role === 'EXPERT'
              ? t('Aucun éleveur ne vous a encore invité à consulter son exploitation.')
              : (
                <>
                  {t('Créez votre exploitation depuis les')}{' '}
                  <Link to="/parametres" className="text-brand-700 hover:underline">
                    {t('paramètres')}
                  </Link>
                  .
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
      <PageHeader
        title={t('Bonjour {{name}}', { name: user?.first_name ?? '' })}
        description={scope ? t("Vue d'ensemble : {{scope}}.", { scope }) : undefined}
      />

      <TodayTasks farmId={selectedFarmId} />

      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <StatCard label={t('Animaux présents')} value={d.animals.total} icon={<PawPrint className="size-5" />}
          hint={
            d.animals.total
              ? t('{{females}} femelle(s), {{males}} mâle(s)', { females: d.animals.by_sex.F, males: d.animals.by_sex.M })
              : t('Aucun animal enregistré')
          } />
        <StatCard label={t('Lots actifs')} value={d.groups_count} icon={<Layers className="size-5" />} />
        <StatCard label={t('Pesées (30 derniers jours)')} value={d.weighings.last_30_days} icon={<Scale className="size-5" />}
          hint={d.weighings.never_weighed ? t('{{count}} animal(aux) jamais pesé(s)', { count: d.weighings.never_weighed }) : undefined} />
        <StatCard
          label={t("Coût d'alimentation estimé (30 j)")}
          value={cost.estimated_cost !== null ? formatMoney(cost.estimated_cost, cost.currency) : '—'}
          icon={<Wallet className="size-5" />}
          hint={
            cost.records === 0
              ? t('Aucune distribution enregistrée')
              : cost.records_without_cost
                ? t('{{without}} distribution(s) sur {{total}} sans coût connu', { without: cost.records_without_cost, total: cost.records })
                : t('Sur {{count}} distribution(s)', { count: cost.records })
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={t('Troupeau')}>
          {d.animals.total === 0 ? (
            <EmptyState title={t('Aucun animal')}>
              <Link to="/animaux/nouveau" className="text-brand-700 hover:underline">{t('Ajouter un animal')}</Link>
            </EmptyState>
          ) : (
            <>
              <ul className="space-y-3">
                {d.animals.by_category.map((c) => (
                  <li key={c.name}>
                    <div className="flex justify-between gap-3 text-sm">
                      <span className="text-slate-700">{t(c.name)}</span>
                      <span className="font-semibold text-slate-900 tabular-nums">{c.count}</span>
                    </div>
                    <div className="mt-1 h-1.5 rounded-full bg-slate-100" aria-hidden>
                      <div className="h-full rounded-full bg-brand-600" style={{ width: `${Math.max(4, (c.count / d.animals.total) * 100)}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-sm text-slate-500">{t('Espèces :')} {d.animals.by_species.map((s) => `${t(s.name)} (${s.count})`).join(', ')}</p>
            </>
          )}
        </Card>
        <Card title={t('Évolution du poids')}>
          {d.weight_trend.points.length === 0 ? (
            <EmptyState title={t('Aucune pesée sur les six derniers mois')} />
          ) : (
            <>
              <WeightTrendChart points={d.weight_trend.points} />
              <p className="mt-2 text-sm text-slate-500">{d.weight_trend.note}</p>
            </>
          )}
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={t('Dernières pesées')} actions={<Link to="/suivi-croissance" className="text-sm font-medium text-brand-700 hover:underline">{t('Suivi')}</Link>}>
          {d.weighings.latest.length === 0 ? (
            <EmptyState title={t('Aucune pesée')} />
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {d.weighings.latest.map((w) => (
                <li key={w.id} className="flex items-center justify-between gap-2 py-2 first:pt-0">
                  <Link to={`/animaux/${w.animal_id}`} className="flex min-w-0 items-center gap-2 hover:opacity-80">
                    {w.tag_number ? <AnimalTag>{w.tag_number}</AnimalTag> : <span className="text-brand-700">{w.animal}</span>}
                    {w.animal_name && <span className="truncate text-slate-600">{w.animal_name}</span>}
                  </Link>
                  <span className="shrink-0 text-slate-600">{formatNumber(w.weight_kg)} kg · {formatDate(w.weighed_on)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title={t('Rations en cours')}>
          {d.rations.active_count === 0 ? (
            <EmptyState title={t('Aucune ration en cours')}>
              {t("Une ration se crée à partir d'une formule validée par un expert.")}{' '}
              <Link to="/rations" className="font-semibold text-brand-700 hover:underline">{t('Voir les rations')}</Link>
            </EmptyState>
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {d.rations.active.map((r) => (
                <li key={r.id} className="py-2 first:pt-0">
                  <p className="font-medium text-slate-800">{r.name}</p>
                  <p className="text-xs text-slate-500">{r.target} · {t('depuis le {{date}}', { date: formatDate(r.start_date) })} · {t(r.formula_status)}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className={isAdmin ? 'grid gap-6 lg:grid-cols-3' : ''}>
        <Card title={t('Activités récentes')} className={isAdmin ? 'lg:col-span-2' : undefined}>
          {d.recent_activity.length === 0 ? (
            <EmptyState title={t('Aucune activité enregistrée')} />
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {d.recent_activity.map((e) => (
                <li key={e.id} className="flex flex-wrap justify-between gap-2 py-2 first:pt-0">
                  <span className="text-slate-700">
                    <span className="font-medium">{t(e.label)}</span>
                    {e.object && <span className="text-slate-600"> · {e.object}</span>}
                  </span>
                  <span className="text-xs text-slate-500">{e.actor ?? '—'} · {formatDateTime(e.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        {isAdmin && (
        <Card title={t('Services')}>
          {health.isPending ? (
            <Spinner />
          ) : health.isError ? (
            <Alert tone="error">{health.error.message}</Alert>
          ) : (
            <ul className="space-y-2 text-sm text-slate-600">
              <li>
                {t('Base de données :')} {health.data.database.connected ? t('connectée') : t('inaccessible')}
              </li>
              <li>
                {t('Assistant IA :')}{' '}
                {health.data.assistant.configured
                  ? t('configuré ({{provider}})', { provider: health.data.assistant.provider })
                  : t('non configuré — les autres modules restent utilisables')}
              </li>
            </ul>
          )}
        </Card>
        )}
      </div>
    </div>
  )
}
