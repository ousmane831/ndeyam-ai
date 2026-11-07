import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Alert, Badge } from '@/components/ui/Feedback'
import { Modal } from '@/components/ui/Modal'
import type { ValidationStatus, WorkflowAction } from '@/types/nutrition'

const STATUS: Record<ValidationStatus, { label: string; tone: 'neutral' | 'warning' | 'brand' | 'danger' }> = {
  DRAFT: { label: 'Brouillon', tone: 'neutral' },
  PENDING: { label: 'En attente de validation', tone: 'warning' },
  VALIDATED: { label: 'Validé', tone: 'brand' },
  REJECTED: { label: 'Rejeté', tone: 'danger' },
}

export function ValidationBadge({ status, isDemo }: { status: ValidationStatus; isDemo?: boolean }) {
  return (
    <span className="inline-flex flex-wrap gap-1">
      <Badge tone={STATUS[status].tone}>{STATUS[status].label}</Badge>
      {isDemo && <Badge tone="demo">DEMO</Badge>}
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
      setError(e instanceof Error ? e.message : 'Action impossible.')
    } finally {
      setPending(null)
    }
  }

  const actions: { action: WorkflowAction; label: string; show: boolean; variant: 'primary' | 'secondary' | 'ghost' | 'danger' }[] = [
    { action: 'submit', label: 'Soumettre à validation', show: canSubmit && (status === 'DRAFT' || status === 'REJECTED'), variant: 'secondary' },
    { action: 'validate', label: 'Valider', show: isReviewer && (status === 'DRAFT' || status === 'PENDING'), variant: 'primary' },
    { action: 'reject', label: 'Rejeter', show: isReviewer && (status === 'PENDING' || status === 'VALIDATED'), variant: 'secondary' },
    { action: 'revert', label: 'Remettre en brouillon', show: isReviewer && status !== 'DRAFT', variant: 'ghost' },
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
        title="Rejeter cette donnée"
        onClose={() => setRejecting(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setRejecting(false)}>
              Annuler
            </Button>
            <Button variant="danger" loading={pending === 'reject'} disabled={!comment.trim()} onClick={() => run('reject', comment.trim())}>
              Rejeter
            </Button>
          </>
        }
      >
        <label htmlFor="reject-comment" className="mb-1.5 block text-sm font-medium text-slate-700">
          Motif du rejet <span className="text-red-600">*</span>
        </label>
        <textarea id="reject-comment" rows={3} value={comment} onChange={(e) => setComment(e.target.value)}
          className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <p className="mt-1 text-xs text-slate-500">Le motif est conservé dans l'historique des validations.</p>
      </Modal>
    </div>
  )
}
