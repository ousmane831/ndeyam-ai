import clsx from 'clsx'
import { Bean, Leaf, Package, Pill, Shell, Sprout, Wheat } from 'lucide-react'
import type { ComponentType } from 'react'

/** Pictogramme par famille d'aliment : se reconnaît sans lire (catégories du référentiel). */
const ICONS: Record<string, { icon: ComponentType<{ className?: string }>; label: string }> = {
  CEREALES: { icon: Wheat, label: 'Céréale' },
  SOUS_PRODUITS_CEREALIERS: { icon: Wheat, label: 'Son, issue de céréale' },
  TOURTEAUX: { icon: Bean, label: 'Tourteau, graine' },
  FOURRAGES: { icon: Leaf, label: 'Fourrage' },
  RESIDUS_CULTURE: { icon: Sprout, label: 'Fane, paille' },
  SOURCES_MINERALES: { icon: Shell, label: 'Minéral' },
  COMPLEMENTS: { icon: Pill, label: 'Complément' },
}

export function IngredientIcon({ category, size = 'md' }: { category?: string | null; size?: 'md' | 'lg' }) {
  const entry = (category && ICONS[category]) || { icon: Package, label: 'Aliment' }
  const Icon = entry.icon
  return (
    <span title={entry.label} className={clsx('inline-flex shrink-0 items-center justify-center rounded-full bg-mil-100 text-mil-700', size === 'lg' ? 'size-12' : 'size-10')}>
      <Icon className={size === 'lg' ? 'size-6' : 'size-5'} aria-hidden />
    </span>
  )
}
