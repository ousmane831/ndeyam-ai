import { lazy, Suspense, type ComponentProps } from 'react'
import { Spinner } from '@/components/ui/Spinner'

/* Les graphiques (Recharts) sont chargés à la demande pour alléger le chargement initial. */
const WeightChartLazy = lazy(() => import('@/features/growth/WeightChart'))
const DistributionChartLazy = lazy(() =>
  import('@/features/dashboard/DashboardCharts').then((m) => ({ default: m.DistributionChart })),
)
const WeightTrendChartLazy = lazy(() =>
  import('@/features/dashboard/DashboardCharts').then((m) => ({ default: m.WeightTrendChart })),
)

const fallback = (
  <div className="flex h-56 items-center justify-center">
    <Spinner label="Chargement du graphique…" />
  </div>
)

export function WeightChart(props: ComponentProps<typeof WeightChartLazy>) {
  return (
    <Suspense fallback={fallback}>
      <WeightChartLazy {...props} />
    </Suspense>
  )
}

export function DistributionChart(props: ComponentProps<typeof DistributionChartLazy>) {
  return (
    <Suspense fallback={fallback}>
      <DistributionChartLazy {...props} />
    </Suspense>
  )
}

export function WeightTrendChart(props: ComponentProps<typeof WeightTrendChartLazy>) {
  return (
    <Suspense fallback={fallback}>
      <WeightTrendChartLazy {...props} />
    </Suspense>
  )
}
