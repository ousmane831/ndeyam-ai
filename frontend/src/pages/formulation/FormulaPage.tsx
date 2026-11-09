import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, RotateCcw, Send, Trash2, Wheat } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, Card } from '@/components/ui/Feedback'
import { FormulaStatus } from '@/features/formulation/FormulaStatus'
import { PageHeader } from '@/components/ui/Layout'
import { ConfirmDialog, Modal } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { FormulaResult } from '@/features/formulation/FormulaResult'
import { rationBlocker } from '@/features/formulation/rationRules'
import type { Formula } from '@/types/formula'
import { useAuth } from '@/hooks/useAuth'
import { useFarm } from '@/hooks/useFarm'
import { formulaService } from '@/services/formulas'
import { formatDateTime } from '@/utils/format'

/** Après un refus ou une impossibilité : ce qu'il faut compléter, et comment relancer le calcul. */
function RecoverySteps({ formula, writable }: { formula: Formula; writable: boolean }) {
  const excluded = formula.result_snapshot.excluded_ingredients ?? []
  const noReference = (formula.result_snapshot.refusal_reasons ?? []).some((r) => /référence/i.test(r))
  return (
    <Card title="Que faire maintenant ?">
      <ol className="space-y-3 text-sm text-slate-700">
        {excluded.map((e) => (
          <li key={e.ingredient_id} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span><strong className="font-semibold text-slate-900">{e.name}</strong> : {e.reasons.join(' ; ')}.</span>
            <Link to={`/ingredients/${e.ingredient_id}`} className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline">
              Compléter cet ingrédient <ArrowRight className="size-4" aria-hidden />
            </Link>
          </li>
        ))}
        {noReference && (
          <li className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span>Aucune référence nutritionnelle validée ne correspond à ce profil d'animal : un expert doit en saisir et en valider une.</span>
            <Link to="/references" className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline">
              Voir les références <ArrowRight className="size-4" aria-hidden />
            </Link>
          </li>
        )}
        {formula.status === 'INFEASIBLE' && (
          <li>Ajoutez un ingrédient plus riche sur le point bloquant indiqué ci-dessus, ou faites revoir la contrainte par un expert.</li>
        )}
      </ol>
      {writable && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <Link to={`/formulation?onglet=calcul&depuis=${formula.id}`}
            className="inline-flex min-h-11 items-center gap-2 rounded-md bg-brand-800 px-4 text-sm font-semibold text-white hover:bg-brand-700">
            <RotateCcw className="size-4" aria-hidden /> Modifier et recalculer
          </Link>
        </div>
      )}
    </Card>
  )
}

export function FormulaPage() {
  const { id } = useParams()
  const formulaId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { canWrite, farms } = useFarm()
  const formula = useQuery({ queryKey: ['formula', formulaId], queryFn: () => formulaService.get(formulaId) })
  const [reviewing, setReviewing] = useState<'validate' | 'reject' | null>(null)
  const [comment, setComment] = useState('')
  const [deleting, setDeleting] = useState(false)

  const review = useMutation({
    mutationFn: ({ action, text }: { action: 'submit-review' | 'validate' | 'reject'; text: string }) => formulaService.review(formulaId, action, text),
    onSuccess: (updated) => {
      queryClient.setQueryData(['formula', formulaId], updated)
      queryClient.invalidateQueries({ queryKey: ['formulas'] })
      setReviewing(null)
      setComment('')
    },
  })
  const removal = useMutation({
    mutationFn: () => formulaService.remove(formulaId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['formulas'] })
      navigate('/formulation?onglet=formules')
    },
  })

  if (formula.isPending) return <Spinner />
  if (formula.isError) return <Alert tone="error">{formula.error.message}</Alert>
  const f = formula.data
  const writable = canWrite(f.farm)
  const isExpertHere = user?.is_platform_admin || (user?.role === 'EXPERT' && farms.some((x) => x.id === f.farm))
  const canSubmit = writable && ['DRAFT', 'ESTIMATED', 'REJECTED'].includes(f.status) && f.items.length > 0
  const canReview = isExpertHere && f.status === 'PENDING_REVIEW'
  const rationProblem = rationBlocker(f)
  const canRation = writable && f.items.length > 0 && rationProblem === null
  const needsRecovery = f.status === 'REFUSED' || f.status === 'INFEASIBLE'

  return (
    <div className="space-y-6">
      <Link to="/formulation?onglet=formules" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"><ArrowLeft className="size-4" /> Formules</Link>
      <PageHeader
        title={f.name}
        description={<span className="flex flex-wrap items-center gap-2">{f.mode_label} · {formatDateTime(f.created_at)} <FormulaStatus status={f.status} label={f.status_label} isDemo={f.is_demo} /></span>}
        actions={
          <>
            {canSubmit && <Button icon={<Send className="size-4" />} loading={review.isPending} onClick={() => review.mutate({ action: 'submit-review', text: '' })}>Demander la vérification d'un expert</Button>}
            {canReview && <><Button onClick={() => setReviewing('validate')}>Valider</Button><Button variant="secondary" onClick={() => setReviewing('reject')}>Rejeter</Button></>}
            {canRation && <Button variant="secondary" icon={<Wheat className="size-4" />} onClick={() => navigate(`/rations?formule=${f.id}`)}>Créer une ration</Button>}
            {writable && <Button variant="ghost" icon={<Trash2 className="size-4" />} onClick={() => setDeleting(true)}>Supprimer</Button>}
          </>
        }
      />
      {review.isError && <Alert tone="error">{review.error.message}</Alert>}
      {writable && f.items.length > 0 && rationProblem && !needsRecovery && (
        <p className="text-sm text-slate-600">{rationProblem}</p>
      )}
      <FormulaResult formula={f} />
      {needsRecovery && <RecoverySteps formula={f} writable={writable} />}

      <Modal open={reviewing !== null} title={reviewing === 'validate' ? 'Valider cette formule' : 'Rejeter cette formule'} onClose={() => setReviewing(null)}
        footer={<>
          <Button variant="secondary" onClick={() => setReviewing(null)}>Annuler</Button>
          <Button variant={reviewing === 'reject' ? 'danger' : 'primary'} loading={review.isPending} disabled={reviewing === 'reject' && !comment.trim()}
            onClick={() => reviewing && review.mutate({ action: reviewing, text: comment.trim() })}>Confirmer</Button>
        </>}>
        <label htmlFor="review-comment" className="mb-1.5 block text-sm font-medium text-slate-700">Commentaire {reviewing === 'reject' && <span className="text-red-600">*</span>}</label>
        <textarea id="review-comment" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        {reviewing === 'validate' && <p className="mt-2 text-xs text-slate-500">En validant, vous attestez avoir vérifié cette formule pour l'usage prévu.</p>}
      </Modal>
      <ConfirmDialog open={deleting} title="Supprimer cette formule ?" danger confirmLabel="Supprimer" loading={removal.isPending}
        message={<>La formule et son détail de calcul seront supprimés.{removal.isError && <span className="mt-2 block text-red-600">{removal.error.message}</span>}</>}
        onConfirm={() => removal.mutate()} onCancel={() => setDeleting(false)} />
    </div>
  )
}
