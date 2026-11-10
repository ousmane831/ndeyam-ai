import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ClipboardCheck, FileWarning, Scale, ShieldCheck, TrendingDown, Wheat } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { Card } from '@/components/ui/Feedback'
import { Spinner } from '@/components/ui/Spinner'
import { t } from '@/i18n'
import { alertService } from '@/services/alerts'
import type { Alert } from '@/types/alert'

interface Task {
  key: string
  icon: ReactNode
  title: string
  detail?: ReactNode
  to: string
  action: string
  urgent?: boolean
}

const animalLink = (a: Alert, tab?: string) =>
  a.target?.type === 'animal' ? `/animaux/${a.target.id}${tab ? `?onglet=${tab}` : ''}` : '/animaux'

/** Regroupe les alertes ouvertes en tâches concrètes, chacune avec son action directe. */
function buildTasks(alerts: Alert[]): Task[] {
  const by = (type: string) => alerts.filter((a) => a.alert_type === type)
  const tasks: Task[] = []
  const names = (list: Alert[]) =>
    list.slice(0, 3).map((a) => a.title.split(' : ').slice(1).join(' : ') || a.title).join(', ') + (list.length > 3 ? '…' : '')

  const weigh = by('WEIGHING_REMINDER')
  if (weigh.length === 1) {
    tasks.push({ key: 'weigh', icon: <Scale className="size-5" />, title: t('1 animal à peser'), detail: names(weigh), to: animalLink(weigh[0], 'pesees'), action: t('Peser'), urgent: true })
  } else if (weigh.length > 1) {
    tasks.push({ key: 'weigh', icon: <Scale className="size-5" />, title: t('{{count}} animaux à peser', { count: weigh.length }), detail: names(weigh), to: '/suivi-croissance', action: t('Séance de pesée'), urgent: true })
  }
  const growth = by('GROWTH_OUT_OF_RANGE')
  if (growth.length) {
    tasks.push({ key: 'growth', icon: <TrendingDown className="size-5" />, title: t('Croissance à surveiller ({{count}})', { count: growth.length }), detail: names(growth), to: growth.length === 1 ? animalLink(growth[0], 'pesees') : '/alertes?type=GROWTH_OUT_OF_RANGE', action: t('Voir'), urgent: true })
  }
  const follow = by('FOLLOW_UP_REMINDER')
  if (follow.length) {
    tasks.push({ key: 'follow', icon: <Wheat className="size-5" />, title: follow.length > 1 ? t('Distributions à enregistrer ({{count}} rations)', { count: follow.length }) : t('Distributions à enregistrer ({{count}} ration)', { count: follow.length }), to: '/rations?onglet=distributions', action: t('Enregistrer') })
  }
  const review = by('FORMULA_TO_REVIEW')
  if (review.length) {
    const target = review.length === 1 && review[0].target?.type === 'feedformula' ? `/formulation/${review[0].target.id}` : '/formulation?onglet=formules'
    tasks.push({ key: 'review', icon: <ClipboardCheck className="size-5" />, title: review.length > 1 ? t("Formules en attente d'un expert ({{count}})", { count: review.length }) : t("Formule en attente d'un expert ({{count}})", { count: review.length }), detail: t('Une ration ne peut être créée qu’après validation.'), to: target, action: t('Voir') })
  }
  const validate = by('REFERENCE_TO_VALIDATE')
  if (validate.length) {
    tasks.push({ key: 'validate', icon: <ShieldCheck className="size-5" />, title: validate[0].title, detail: validate[0].message, to: '/references', action: t('Valider') })
  }
  const missing = by('MISSING_DATA')
  if (missing.length) {
    tasks.push({ key: 'missing', icon: <FileWarning className="size-5" />, title: t('Fiches à compléter ({{count}})', { count: missing.length }), detail: names(missing), to: missing.length === 1 ? animalLink(missing[0]) : '/alertes?type=MISSING_DATA', action: t('Compléter') })
  }
  return tasks
}

export function TodayTasks({ farmId }: { farmId: number | null }) {
  const { t } = useTranslation()
  const alerts = useQuery({ queryKey: ['alerts', 'today', farmId], queryFn: () => alertService.list({ farm: farmId, page: 1 }) })
  const tasks = alerts.data ? buildTasks(alerts.data.results.filter((a) => a.status === 'OPEN' || a.status === 'ACKNOWLEDGED')) : []

  return (
    <Card
      title={t("À faire aujourd'hui")}
      actions={
        <Link to="/alertes" className="text-sm font-semibold text-brand-700 hover:underline">
          {t('Toutes les alertes')}
        </Link>
      }
    >
      {alerts.isPending ? <Spinner /> : alerts.isError ? (
        <p className="text-sm text-slate-500">{t("Les tâches du jour n'ont pas pu être chargées. Consultez la page Alertes.")}</p>
      ) : tasks.length === 0 ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-slate-600">{t("Rien d'urgent : aucune pesée en retard ni action en attente.")}</p>
          <Link to="/suivi-croissance" className="inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-brand-700 hover:underline">
            {t('Enregistrer une pesée')} <ArrowRight className="size-4" aria-hidden />
          </Link>
        </div>
      ) : (
        <ul className="-my-2 divide-y divide-slate-100">
          {tasks.map((task) => (
            <li key={task.key} className="flex items-center gap-3 py-3">
              <span className={task.urgent ? 'flex size-10 shrink-0 items-center justify-center rounded-md bg-mil-100 text-mil-700' : 'flex size-10 shrink-0 items-center justify-center rounded-md bg-brand-50 text-brand-700'}>
                {task.icon}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-slate-900">{task.title}</p>
                {task.detail && <p className="truncate text-sm text-slate-500">{task.detail}</p>}
              </div>
              <Link to={task.to} className="inline-flex min-h-11 shrink-0 items-center gap-1.5 rounded-md bg-brand-800 px-3.5 text-sm font-semibold text-white hover:bg-brand-700">
                {task.action} <ArrowRight className="size-4" aria-hidden />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
