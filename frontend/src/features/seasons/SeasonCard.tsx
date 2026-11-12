import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { ArrowRight, Droplets, Home, Lightbulb, Timer, Wheat } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { Stamp } from '@/components/ui/Feedback'
import { seasonService } from '@/services/seasons'
import type { AdviceTopic } from '@/types/season'
import { SeasonIcon } from './SeasonCalendar'
import { seasonTone } from './seasonStyle'

const TOPIC_ICON: Record<AdviceTopic, typeof Droplets> = { WATER: Droplets, FEED: Wheat, SCHEDULE: Timer, HOUSING: Home, OTHER: Lightbulb }

/** Accueil : saison en cours et ses conseils validés (une icône par thème : eau, aliments, horaires, abri). */
export function SeasonCard({ farmId }: { farmId: number | null }) {
  const { t } = useTranslation()
  const current = useQuery({ queryKey: ['season-current', farmId], queryFn: () => seasonService.current(farmId) })
  const season = current.data?.season
  if (!season) return null
  const advice = current.data?.advice ?? []
  return (
    <section aria-labelledby="season-card" className="overflow-hidden rounded-md border border-slate-200 bg-white">
      <header className={clsx('flex items-center gap-3 px-5 py-3', seasonTone(season))}>
        <SeasonIcon season={season} className="size-6" />
        <div className="min-w-0 flex-1">
          <h2 id="season-card" className="font-display text-lg font-bold">{t(season.name)}</h2>
          <p className="text-sm opacity-90">{t(season.description)}</p>
        </div>
      </header>
      <div className="space-y-3 px-5 py-4">
        {advice.length === 0 ? (
          <p className="text-sm text-slate-600">{t('Aucun conseil validé pour cette saison. Les conseils sont publiés après validation par un spécialiste.')}</p>
        ) : (
          <ul className="space-y-3">
            {advice.slice(0, 4).map((a) => {
              const Icon = TOPIC_ICON[a.topic] ?? Lightbulb
              return (
                <li key={a.id} className="flex gap-3">
                  <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-full bg-brand-50 text-brand-700"><Icon className="size-5" aria-hidden /></span>
                  <span className="min-w-0">
                    <span className="flex flex-wrap items-center gap-2 font-semibold text-slate-900">{a.title}{a.is_demo && <Stamp tone="demo">DEMO</Stamp>}</span>
                    <span className="block text-sm text-slate-600">{a.text}</span>
                  </span>
                </li>
              )
            })}
          </ul>
        )}
        <Link to="/saisons" className="inline-flex min-h-10 items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">
          {t('Prix, disponibilité et conseils par saison')} <ArrowRight className="size-4" aria-hidden />
        </Link>
      </div>
    </section>
  )
}
