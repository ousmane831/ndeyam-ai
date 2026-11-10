import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/Button'
import { Alert, Stamp, type StampTone } from '@/components/ui/Feedback'
import { Modal } from '@/components/ui/Modal'
import { tk } from '@/i18n'
import type { ValidationStatus, WorkflowAction } from '@/types/nutrition'

const STATUS: Record<ValidationStatus, { label: string; tone: StampTone }> = {
  DRAFT: { label: tk('Brouillon'), tone: 'neutral' },
  PENDING: { label: tk('En attente de validation'), tone: 'pending' },
  VALIDATED: { label: tk('Validé'), tone: 'ok' },
  REJECTED: { label: tk('Rejeté'), tone: 'danger' },
}

export function ValidationBadge({ status, isDemo }: { status: ValidationStatus; isDemo?: boolean }) {
  const { t } = useTranslation()
  return (
    <span className="inline-flex flex-wrap gap-1">
      <Stamp tone={STATUS[status].tone}>{t(STATUS[status].label)}</Stamp>
      {isDemo && <Stamp tone="demo">DEMO</Stamp>}
    </span>
  )
}

/**
 * Actions du circuit de validation. Le serveur reste juge : cette barre n'affiche que les
 * actions plausibles pour l'utilisateur et le statut courant.
 */
export function WorkflowActions({
  status,
  canSubmit,
  isReviewer,
  onAction,
  size = 'sm',
}: {
  status: ValidationStatus
  canSubmit: boolean
  isReviewer: boolean
  onAction: (action: WorkflowAction, comment: string) => Promise<unknown>
  size?: 'sm' | 'md'
}) {
  const { t } = useTranslation()
  const [pending, setPending] = useState<WorkflowAction | null>(null)
  const [rejecting, setRejecting] = useState(false)
  const [comment, setComment] = useState('')
  const [error, setError] = useState<string | null>(null)

  const run = async (action: WorkflowAction, text = '') => {
    setError(null)
    setPending(action)
    try {
      await onAction(action, text)
      setRejecting(false)
      setComment('')
    } catch (e) {
      setError(e instanceof Error ? e.message : t('Action impossible.'))
    } finally {
      setPending(null)
    }
  }

  const actions: { action: WorkflowAction; label: string; show: boolean; variant: 'primary' | 'secondary' | 'ghost' | 'danger' }[] = [
    { action: 'submit', label: t('Soumettre à validation'), show: canSubmit && (status === 'DRAFT' || status === 'REJECTED'), variant: 'secondary' },
    { action: 'validate', label: t('Valider'), show: isReviewer && (status === 'DRAFT' || status === 'PENDING'), variant: 'primary' },
    { action: 'reject', label: t('Rejeter'), show: isReviewer && (status === 'PENDING' || status === 'VALIDATED'), variant: 'secondary' },
    { action: 'revert', label: t('Remettre en brouillon'), show: isReviewer && status !== 'DRAFT', variant: 'ghost' },
  ]
  const visible = actions.filter((a) => a.show)
  if (visible.length === 0) return null

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {visible.map((a) => (
          <Button key={a.action} size={size} variant={a.variant} loading={pending === a.action} disabled={pending !== null}
            onClick={() => (a.action === 'reject' ? setRejecting(true) : run(a.action))}>
            {a.label}
          </Button>
        ))}
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      <Modal
        open={rejecting}
        title={t('Rejeter cette donnée')}
        onClose={() => setRejecting(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setRejecting(false)}>
              {t('Annuler')}
            </Button>
            <Button variant="danger" loading={pending === 'reject'} disabled={!comment.trim()} onClick={() => run('reject', comment.trim())}>
              {t('Rejeter')}
            </Button>
          </>
        }
      >
        <label htmlFor="reject-comment" className="mb-1.5 block text-sm font-medium text-slate-700">
          {t('Motif du rejet')} <span className="text-red-600">*</span>
        </label>
        <textarea id="reject-comment" rows={3} value={comment} onChange={(e) => setComment(e.target.value)}
          className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <p className="mt-1 text-xs text-slate-500">{t("Le motif est conservé dans l'historique des validations.")}</p>
      </Modal>
    </div>
  )
}
