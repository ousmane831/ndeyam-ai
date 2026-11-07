import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART, axisTick, niceTicks } from '@/features/charts/theme'
import type { DashboardData } from '@/types/dashboard'
import { formatMonth, formatNumber } from '@/utils/format'

const PALETTE = CHART.series

export function DistributionChart({ data }: { data: { name: string; count: number }[] }) {
  return (
    <div className="h-56 w-full" role="img" aria-label="Répartition des animaux">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
          <CartesianGrid stroke={CHART.grid} horizontal={false} />
          <XAxis type="number" allowDecimals={false} tick={axisTick} tickLine={false} axisLine={false} />
          <YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 12, fill: CHART.axisStrong }} tickLine={false} axisLine={{ stroke: CHART.grid }} />
          <Tooltip formatter={(v) => [String(v), 'Animaux']} />
          <Bar dataKey="count" radius={[0, 2, 2, 0]} barSize={18} isAnimationActive={false}>
            {data.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function WeightTrendChart({ points }: { points: DashboardData['weight_trend']['points'] }) {
  const ticks = niceTicks(points.map((p) => Number(p.mean_weight_kg)))
  return (
    <div className="h-56 w-full" role="img" aria-label="Évolution du poids moyen des pesées">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 22, right: 28, bottom: 4, left: 0 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis dataKey="month" tickFormatter={formatMonth} tick={axisTick} tickLine={false} axisLine={{ stroke: CHART.grid }} padding={{ left: 16, right: 36 }} />
          <YAxis tick={axisTick} tickFormatter={(v: number) => formatNumber(v, 0)} ticks={ticks} tickLine={false} axisLine={false} domain={[ticks[0], ticks[ticks.length - 1]]} width={44} label={{ value: 'kg', position: 'insideTopLeft', offset: 0, dy: -10, dx: 6, style: { ...axisTick } }} />
          <Tooltip
            formatter={(value, _name, item) => [
              `${formatNumber(Number(value), 1)} kg (${(item.payload as { weighings: number }).weighings} pesées)`,
              'Poids moyen',
            ]}
            labelFormatter={(label) => formatMonth(String(label))}
          />
          <Line type="linear" dataKey="mean_weight_kg" stroke={CHART.growth} strokeWidth={2.5} dot={{ r: 3.5, fill: '#ffffff', stroke: CHART.growth, strokeWidth: 2 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
