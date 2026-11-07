/** Couleurs des graphiques, alignées sur les jetons de l'identité (src/index.css). */
export const CHART = {
  growth: '#5d7a3a', // acacia : croissance, mesures réelles
  growthFill: '#5d7a3a',
  latest: '#e0a72e', // mil : dernier point / repère
  outline: '#1d2b53', // indigo nuit
  grid: '#e6e9ef',
  axis: '#636d80',
  axisStrong: '#363e50',
  /** Catégories (répartition) : indigo puis mil, du plus foncé au plus clair. */
  series: ['#1d2b53', '#2e4482', '#5f76b0', '#e0a72e', '#8e9fcc', '#c98f1c'],
  font: "'IBM Plex Mono', ui-monospace, monospace",
}

export const axisTick = { fontSize: 11, fill: CHART.axis, fontFamily: CHART.font }

/** Graduations régulières (pas de 1, 2, 5, 10… kg) couvrant les valeurs, 4 à 6 repères. */
export function niceTicks(values: number[]): number[] {
  const finite = values.filter((v) => Number.isFinite(v))
  if (finite.length === 0) return []
  const min = Math.min(...finite)
  const max = Math.max(...finite)
  const span = Math.max(max - min, 1)
  const raw = span / 4
  const magnitude = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 5, 10].map((m) => m * magnitude).find((s) => s >= raw) ?? 10 * magnitude
  const start = Math.floor((min - step * 0.25) / step) * step
  const end = Math.ceil((max + step * 0.25) / step) * step
  const ticks: number[] = []
  for (let t = start; t <= end + step / 2; t += step) ticks.push(Math.round(t * 100) / 100)
  return ticks
}
