import type { Season } from '@/types/season'

/** Couleur d'une saison : mil (chaude), acacia (hivernage), indigo clair (sèche fraîche). */
const TONE: Record<string, string> = {
  hot: 'bg-mil-300 text-brand-900',
  rain: 'bg-acacia-700 text-white',
  cool: 'bg-brand-200 text-brand-900',
}
export const seasonTone = (s: Pick<Season, 'code' | 'is_hot'>) => (s.is_hot ? TONE.hot : s.code === 'HIVERNAGE' ? TONE.rain : TONE.cool)

