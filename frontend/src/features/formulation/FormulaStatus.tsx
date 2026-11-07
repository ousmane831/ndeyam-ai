import { Stamp, type StampTone } from '@/components/ui/Feedback'

/** Un tampon se lit d'un coup d'œil : un mot. Le libellé complet reste disponible (survol, lecteur d'écran). */
const STAMP: Record<string, { tone: StampTone; word: string }> = {
  VALIDATED: { tone: 'ok', word: 'Validée' },
  ESTIMATED: { tone: 'pending', word: 'Estimation' },
  PENDING_REVIEW: { tone: 'pending', word: 'À vérifier' },
  DRAFT: { tone: 'neutral', word: 'Brouillon' },
  REFUSED: { tone: 'danger', word: 'Refusée' },
  INFEASIBLE: { tone: 'danger', word: 'Impossible' },
  REJECTED: { tone: 'danger', word: 'Rejetée' },
}

/** Statut d'une formule sous forme de tampon ; une formule DEMO porte en plus le tampon DEMO. */
export function FormulaStatus({ status, label, isDemo }: { status: string; label: string; isDemo?: boolean }) {
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <Stamp tone={STAMP[status]?.tone ?? 'neutral'} title={label}>
        <span aria-hidden>{STAMP[status]?.word ?? label}</span>
        <span className="sr-only">{label}</span>
      </Stamp>
      {isDemo && <Stamp tone="demo">DEMO</Stamp>}
    </span>
  )
}
