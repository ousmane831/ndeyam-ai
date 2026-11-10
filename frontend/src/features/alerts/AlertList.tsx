import { useMutation, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { AlertTriangle, Bell, CheckCircle2, Eye, Info, Scale, XCircle } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert as Notice, Badge, EmptyState } from '@/components/ui/Feedback'
import { alertService } from '@/services/alerts'
import type { Alert } from '@/types/alert'
import { formatDate, formatDateTime } from '@/utils/format'

const SEVERITY = {
  INFO: { icon: <Info className="size-5" />, tone: 'text-brand-700 bg-brand-50' },
  WARNING: { icon: <AlertTriangle className="size-5" />, tone: 'text-mil-700 bg-mil-100' },
  CRITICAL: { icon: <XCircle className="size-5" />, tone: 'text-red-600 bg-red-50' },
} as const

function TriggerDetails({ data }: { data: Record<string, unknown> }) {
  const { t } = useTranslation()
  const entries = Object.entries(data).filter(([, v]) => v !== null && typeof v !== 'object')
  if (!entries.length) return null
  return (
    <details className="mt-2 text-xs text-slate-500">
      <summary className="cursor-pointer select-none">{t('Pourquoi cette alerte ?')}</summary>
      <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
        {entries.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="font-mono">{k}</dt>
            <dd>{String(v)}</dd>
          </div>
        ))}
      </dl>
    </details>
  )
}

export function AlertList({ alerts, canAct, emptyTitle }: { alerts: Alert[]; canAct: (a: Alert) => boolean; emptyTitle?: string }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const action = useMutation({
    mutationFn: ({ id, kind }: { id: number; kind: 'acknowledge' | 'resolve' | 'dismiss' }) => alertService.act(id, kind),
    onSuccess: () => {
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
    onError: (e: Error) => setError(e.message),
  })

  if (alerts.length === 0) return <EmptyState icon={<Bell className="size-10" />} title={emptyTitle ?? t('Aucune alerte')} />

  return (
    <div className="space-y-3">
      {error && <Notice tone="error">{error}</Notice>}
      <ul className="divide-y divide-slate-100">
        {alerts.map((a) => {
          const severity = SEVERITY[a.severity]
          const open = a.status === 'OPEN' || a.status === 'ACKNOWLEDGED'
          return (
            <li key={a.id} className="flex gap-3 py-4 first:pt-0 last:pb-0">
              <span className={clsx('mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full', severity.tone)}>{severity.icon}</span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium text-slate-800">{a.title}</p>
                  <Badge>{t(a.alert_type_label)}</Badge>
                  {a.status !== 'OPEN' && <Badge tone="neutral">{t(a.status_label)}</Badge>}
                </div>
                <p className="mt-1 text-sm text-slate-600">{a.message}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {a.farm_name && `${a.farm_name} · `}
                  {formatDateTime(a.created_at)}
                  {a.due_date && ` · ${t('échéance {{date}}', { date: formatDate(a.due_date) })}`}
                  {a.target?.type === 'animal' && (
                    <>
                      {' · '}
                      <Link to={`/animaux/${a.target.id}`} className="text-brand-700 hover:underline">
                        {t("voir l'animal")}
                      </Link>
                    </>
                  )}
                </p>
                <TriggerDetails data={a.trigger_data} />
                {open && canAct(a) && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {a.alert_type === 'WEIGHING_REMINDER' && a.target?.type === 'animal' && (
                      <Link to={`/animaux/${a.target.id}?onglet=pesees`}
                        className="inline-flex items-center gap-2 rounded-md bg-brand-800 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700">
                        <Scale className="size-4" aria-hidden /> {t('Peser maintenant')}
                      </Link>
                    )}
                    {a.status === 'OPEN' && (
                      <Button size="sm" variant="secondary" icon={<Eye className="size-4" />} disabled={action.isPending}
                        onClick={() => action.mutate({ id: a.id, kind: 'acknowledge' })}>
                        {t('Prendre en compte')}
                      </Button>
                    )}
                    <Button size="sm" variant="secondary" icon={<CheckCircle2 className="size-4" />} disabled={action.isPending}
                      onClick={() => action.mutate({ id: a.id, kind: 'resolve' })}>
                      {t('Résolue')}
                    </Button>
                    <Button size="sm" variant="ghost" disabled={action.isPending} onClick={() => action.mutate({ id: a.id, kind: 'dismiss' })}>
                      {t('Ignorer')}
                    </Button>
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
