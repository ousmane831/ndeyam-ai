import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DashboardData } from '@/types/dashboard'
import { formatMonth, formatNumber } from '@/utils/format'

const PALETTE = ['#2e7d32', '#52a56c', '#1b4332', '#7cbf91', '#aed8ba']

export function DistributionChart({ data }: { data: { name: string; count: number }[] }) {
  return (
    <div className="h-56 w-full" role="img" aria-label="Répartition des animaux">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12, fill: '#64748b' }} />
          <YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 12, fill: '#334155' }} />
          <Tooltip formatter={(v) => [String(v), 'Animaux']} />
          <Bar dataKey="count" radius={[0, 4, 4, 0]} isAnimationActive={false}>
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
  return (
    <div className="h-56 w-full" role="img" aria-label="Évolution du poids moyen des pesées">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 10, right: 16, bottom: 0, left: -8 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis dataKey="month" tickFormatter={formatMonth} tick={{ fontSize: 12, fill: '#64748b' }} />
          <YAxis unit=" kg" tick={{ fontSize: 12, fill: '#64748b' }} domain={['auto', 'auto']} width={64} />
          <Tooltip
            formatter={(value, _name, item) => [
              `${formatNumber(Number(value), 1)} kg (${(item.payload as { weighings: number }).weighings} pesées)`,
              'Poids moyen',
            ]}
            labelFormatter={(label) => formatMonth(String(label))}
          />
          <Line type="monotone" dataKey="mean_weight_kg" stroke="#2e7d32" strokeWidth={2} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
