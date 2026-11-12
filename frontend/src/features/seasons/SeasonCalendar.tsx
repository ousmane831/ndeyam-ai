import clsx from 'clsx'
import { CloudRain, Sun, Wind } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { currentLocale } from '@/i18n'
import type { Season } from '@/types/season'
import { currentMonth } from '@/utils/format'
import { seasonTone } from './seasonStyle'

/** Pictogramme d'une saison : se reconnaît sans lire. */
export function SeasonIcon({ season, className = 'size-5' }: { season: Pick<Season, 'code' | 'is_hot'>; className?: string }) {
  if (season.is_hot) return <Sun className={className} aria-hidden />
  if (season.code === 'HIVERNAGE') return <CloudRain className={className} aria-hidden />
  return <Wind className={className} aria-hidden />
}

/** Les douze mois de l'année colorés par saison, le mois en cours marqué. */
export function SeasonCalendar({ seasons, month: forcedMonth }: { seasons: Season[]; month?: number }) {
  const { t } = useTranslation()
  const month = forcedMonth ?? currentMonth()
  const monthName = (m: number) => new Intl.DateTimeFormat(currentLocale(), { month: 'short' }).format(new Date(2026, m - 1, 1))
  return (
    <div>
      <ol className="grid grid-cols-6 gap-1 sm:grid-cols-12" aria-label={t('Calendrier des saisons')}>
        {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => {
          const s = seasons.find((x) => x.months.includes(m))
          return (
            <li key={m} className={clsx('flex flex-col items-center gap-1 rounded-md px-1 py-2 text-xs font-semibold', s ? seasonTone(s) : 'bg-slate-100 text-slate-500', m === month && 'ring-2 ring-brand-900 ring-offset-2')}
              title={s ? t(s.name) : undefined} aria-current={m === month ? 'date' : undefined}>
              {s && <SeasonIcon season={s} className="size-4" />}
              <span className="capitalize">{monthName(m)}</span>
            </li>
          )
        })}
      </ol>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-700">
        {seasons.map((s) => (
          <li key={s.id} className="inline-flex items-center gap-2">
            <span className={clsx('inline-flex size-6 items-center justify-center rounded-full', seasonTone(s))}><SeasonIcon season={s} className="size-3.5" /></span>
            {t(s.name)}
          </li>
        ))}
      </ul>
    </div>
  )
}
