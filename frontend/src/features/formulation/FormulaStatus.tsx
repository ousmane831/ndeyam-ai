import { useTranslation } from 'react-i18next'
import { Stamp, type StampTone } from '@/components/ui/Feedback'
import { tk } from '@/i18n'

/** Un tampon se lit d'un coup d'œil : un mot. Le libellé complet reste disponible (survol, lecteur d'écran). */
const STAMP: Record<string, { tone: StampTone; word: string }> = {
  VALIDATED: { tone: 'ok', word: tk('Validée') },
  ESTIMATED: { tone: 'pending', word: tk('Estimation') },
  PENDING_REVIEW: { tone: 'pending', word: tk('À vérifier') },
  DRAFT: { tone: 'neutral', word: tk('Brouillon') },
  REFUSED: { tone: 'danger', word: tk('Refusée') },
  INFEASIBLE: { tone: 'danger', word: tk('Impossible') },
  REJECTED: { tone: 'danger', word: tk('Rejetée') },
}

/** Statut d'une formule sous forme de tampon ; une formule DEMO porte en plus le tampon DEMO. */
export function FormulaStatus({ status, label, isDemo }: { status: string; label: string; isDemo?: boolean }) {
  const { t } = useTranslation()
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <Stamp tone={STAMP[status]?.tone ?? 'neutral'} title={t(label)}>
        <span aria-hidden>{t(STAMP[status]?.word ?? label)}</span>
        <span className="sr-only">{t(label)}</span>
      </Stamp>
      {isDemo && <Stamp tone="demo">DEMO</Stamp>}
    </span>
  )
}
