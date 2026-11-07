import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART, axisTick, niceTicks } from '@/features/charts/theme'
import type { AnimalGrowth } from '@/types/animal'
import { formatDate, formatNumber } from '@/utils/format'

/** Courbe de poids d'un animal (mesures réelles uniquement, aucun point interpolé). */
export default function WeightChart({ growth }: { growth: AnimalGrowth }) {
  const data = growth.points.map((p) => ({
    date: p.date,
    poids: Number(p.weight_kg),
    origin: p.origin,
    method: p.method,
  }))
  const ticks = niceTicks(data.map((d) => d.poids))
  return (
    <div className="h-72 w-full" role="img" aria-label="Courbe d'évolution du poids">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 22, right: 28, bottom: 4, left: 0 }}>
          <CartesianGrid stroke={CHART.grid} vertical={false} />
          <XAxis dataKey="date" tickFormatter={formatDate} tick={axisTick} tickLine={false} axisLine={{ stroke: CHART.grid }} minTickGap={24} padding={{ left: 16, right: 36 }} />
          <YAxis tick={axisTick} tickFormatter={(v: number) => formatNumber(v, 0)} ticks={ticks} tickLine={false} axisLine={false} domain={[ticks[0], ticks[ticks.length - 1]]} width={44} label={{ value: 'kg', position: 'insideTopLeft', offset: 0, dy: -10, dx: 6, style: { ...axisTick } }} />
          <Tooltip
            formatter={(value) => [`${formatNumber(Number(value), 2)} kg`, 'Poids']}
            labelFormatter={(label) => formatDate(String(label))}
          />
          {/* Segments droits : entre deux pesées, rien n'est mesuré, donc rien n'est dessiné en courbe. */}
          <Line
            type="linear"
            dataKey="poids"
            stroke={CHART.growth}
            strokeWidth={2.5}
            isAnimationActive={false}
            dot={(props: { cx?: number; cy?: number; index?: number }) => {
              const last = props.index === data.length - 1
              return (
                <circle key={props.index} cx={props.cx} cy={props.cy} r={last ? 5.5 : 3.5}
                  fill={last ? CHART.latest : '#ffffff'} stroke={last ? CHART.outline : CHART.growth} strokeWidth={2} />
              )
            }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
