import { Activity, Bell, ClipboardCheck, FileWarning, Heart, NotebookPen, Scale, ShieldCheck, Stethoscope, TrendingDown, Wheat } from 'lucide-react'
import type { ComponentType } from 'react'

type Icon = ComponentType<{ className?: string; 'aria-hidden'?: boolean }>

/**
 * Pictogrammes du métier, identiques partout (accueil, alertes, fiches) : on reconnaît la tâche sans lire.
 * Balance = pesée, épi = alimentation, courbe descendante = croissance, presse-papiers coché = vérification,
 * stéthoscope = santé.
 */
const ALERT: Record<string, Icon> = {
  WEIGHING_REMINDER: Scale,
  GROWTH_OUT_OF_RANGE: TrendingDown,
  FOLLOW_UP_REMINDER: Wheat,
  FORMULA_TO_REVIEW: ClipboardCheck,
  REFERENCE_TO_VALIDATE: ShieldCheck,
  MISSING_DATA: FileWarning,
}
const OBSERVATION: Record<string, Icon> = {
  HEALTH: Stethoscope,
  BEHAVIOUR: Activity,
  BEHAVIOR: Activity,
  REPRODUCTION: Heart,
  FEEDING: Wheat,
  GENERAL: NotebookPen,
}

export function AlertTypeIcon({ type, className = 'size-5' }: { type: string; className?: string }) {
  const Icon = ALERT[type] ?? Bell
  return <Icon className={className} aria-hidden />
}

export function ObservationIcon({ kind, className = 'size-5' }: { kind: string; className?: string }) {
  const Icon = OBSERVATION[kind] ?? NotebookPen
  return <Icon className={className} aria-hidden />
}
