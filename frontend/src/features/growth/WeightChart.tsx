import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
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
  return (
    <div className="h-72 w-full" role="img" aria-label="Courbe d'évolution du poids">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 16, bottom: 0, left: -8 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis dataKey="date" tickFormatter={formatDate} tick={{ fontSize: 12, fill: '#64748b' }} minTickGap={24} />
          <YAxis unit=" kg" tick={{ fontSize: 12, fill: '#64748b' }} domain={['auto', 'auto']} width={64} />
          <Tooltip
            formatter={(value) => [`${formatNumber(Number(value), 2)} kg`, 'Poids']}
            labelFormatter={(label) => formatDate(String(label))}
          />
          <Line type="monotone" dataKey="poids" stroke="#2e7d32" strokeWidth={2} dot={{ r: 4, fill: '#2e7d32' }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
