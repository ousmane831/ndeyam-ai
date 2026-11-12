import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, Copy, RotateCcw, Send, Trash2, Wheat } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router'
import { Button } from '@/components/ui/Button'
import { TextField } from '@/components/ui/Field'
import { Alert, Card } from '@/components/ui/Feedback'
import { FormulaStatus } from '@/features/formulation/FormulaStatus'
import { PageHeader } from '@/components/ui/Layout'
import { ConfirmDialog, Modal } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { FormulaResult } from '@/features/formulation/FormulaResult'
import { rationBlocker } from '@/features/formulation/rationRules'
import type { Formula } from '@/types/formula'
import { useFarm } from '@/hooks/useFarm'
import { useRoles } from '@/hooks/useRoles'
import { templateService } from '@/services/formulas'
import { formulaService } from '@/services/formulas'
import { formatDateTime } from '@/utils/format'

/** Après un refus ou une impossibilité : ce qu'il faut compléter, et comment relancer le calcul. */
function RecoverySteps({ formula, writable }: { formula: Formula; writable: boolean }) {
  const { t } = useTranslation()
  const excluded = formula.result_snapshot.excluded_ingredients ?? []
  const noReference = (formula.result_snapshot.refusal_reasons ?? []).some((r) => /référence/i.test(r))
  return (
    <Card title={t('Que faire maintenant ?')}>
      <ol className="space-y-3 text-sm text-slate-700">
        {excluded.map((e) => (
          <li key={e.ingredient_id} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span><strong className="font-semibold text-slate-900">{e.name}</strong> : {e.reasons.join(' ; ')}.</span>
            <Link to={`/ingredients/${e.ingredient_id}`} className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline">
              {t('Compléter cet ingrédient')} <ArrowRight className="size-4" aria-hidden />
            </Link>
          </li>
        ))}
        {noReference && (
          <li className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span>{t("Aucune référence nutritionnelle validée ne correspond à ce profil d'animal : un expert doit en saisir et en valider une.")}</span>
            <Link to="/references" className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline">
              {t('Voir les références')} <ArrowRight className="size-4" aria-hidden />
            </Link>
          </li>
        )}
        {formula.status === 'INFEASIBLE' && (
          <li>{t('Ajoutez un ingrédient plus riche sur le point bloquant indiqué ci-dessus, ou faites revoir la contrainte par un expert.')}</li>
        )}
      </ol>
      {writable && (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <Link to={`/formulation?onglet=calcul&depuis=${formula.id}`}
            className="inline-flex min-h-11 items-center gap-2 rounded-md bg-brand-800 px-4 text-sm font-semibold text-white hover:bg-brand-700">
            <RotateCcw className="size-4" aria-hidden /> {t('Modifier et recalculer')}
          </Link>
        </div>
      )}
    </Card>
  )
}

/** « Enregistrer comme ration type » : brouillon à valider ensuite par un expert (onglet Rations types). */
function SaveAsTemplate({ formula }: { formula: Formula }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const weight = Number(formula.animal_weight_kg ?? 0)
  const [values, setValues] = useState({
    name: formula.name,
    min: weight ? String(Math.floor(weight * 0.9)) : '',
    max: weight ? String(Math.ceil(weight * 1.1)) : '',
    conditions: '',
  })
  const [done, setDone] = useState(false)
  const save = useMutation({
    mutationFn: () => templateService.fromFormula({ formula: formula.id, name: values.name.trim(), weight_min_kg: values.min.replace(',', '.'), weight_max_kg: values.max.replace(',', '.'), conditions: values.conditions }),
    onSuccess: () => { setDone(true); setOpen(false) },
  })
  const set = (k: keyof typeof values) => (e: { target: { value: string } }) => setValues((v) => ({ ...v, [k]: e.target.value }))
  return (
    <>
      {done ? (
        <Alert tone="success" title={t('Ration type enregistrée (brouillon)')}>
          {t('Validez-la dans l’onglet « Rations types » : elle sera alors utilisable tout de suite par les éleveurs dans ce cas.')}{' '}
          <Link to="/formulation?onglet=types" className="font-semibold underline">{t('Rations types')}</Link>
        </Alert>
      ) : (
        <Button variant="secondary" icon={<Copy className="size-4" />} onClick={() => setOpen(true)}>{t('Enregistrer comme ration type')}</Button>
      )}
      <Modal open={open} title={t('Enregistrer comme ration type')} onClose={() => setOpen(false)}
        footer={<>
          <Button variant="secondary" onClick={() => setOpen(false)}>{t('Annuler')}</Button>
          <Button loading={save.isPending} disabled={!values.name.trim() || !values.min || !values.max} onClick={() => save.mutate()}>{t('Enregistrer')}</Button>
        </>}>
        <div className="space-y-3">
          <p className="text-sm text-slate-600">{t('Mêmes aliments, mêmes proportions et même ingestion que cette formule validée, pour la tranche de poids indiquée.')}</p>
          {save.isError && <Alert tone="error">{save.error.message}</Alert>}
          <TextField label={t('Nom')} value={values.name} onChange={set('name')} />
          <div className="grid grid-cols-2 gap-3">
            <TextField label={t('Poids min. (kg)')} inputMode="decimal" value={values.min} onChange={set('min')} />
            <TextField label={t('Poids max. (kg)')} inputMode="decimal" value={values.max} onChange={set('max')} />
          </div>
          <TextField label={t("Conditions d'emploi (facultatif)")} value={values.conditions} onChange={set('conditions')} />
        </div>
      </Modal>
    </>
  )
}

export function FormulaPage() {
  const { t } = useTranslation()
  const { id } = useParams()
  const formulaId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { canWrite, canReviewRations } = useFarm()
  const { isReviewer } = useRoles()
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
  // Seul le nutritionniste / zootechnicien invité (ou l'administrateur) se prononce sur une ration.
  const isExpertHere = canReviewRations(f.farm)
  const canSubmit = writable && ['DRAFT', 'ESTIMATED', 'REJECTED'].includes(f.status) && f.items.length > 0
  const canReview = isExpertHere && f.status === 'PENDING_REVIEW'
  const rationProblem = rationBlocker(f)
  const canRation = writable && f.items.length > 0 && rationProblem === null
  const needsRecovery = f.status === 'REFUSED' || f.status === 'INFEASIBLE'
  // Le nutritionniste fait d'une formule validée une ration type, utilisable ensuite sans attente (DEMO : exemple).
  const canMakeTemplate = f.mode !== 'TEMPLATE' && f.items.length > 0 && (f.status === 'VALIDATED' || (f.is_demo && isReviewer)) && (canReviewRations(f.farm) || (f.is_demo && isReviewer))

  return (
    <div className="space-y-6">
      <Link to="/formulation?onglet=formules" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"><ArrowLeft className="size-4" /> {t('Formules')}</Link>
      <PageHeader
        title={f.name}
        description={<span className="flex flex-wrap items-center gap-2">{t(f.mode_label)} · {formatDateTime(f.created_at)}{f.season_name ? ` · ${t(f.season_name)}` : ''} <FormulaStatus status={f.status} label={f.status_label} isDemo={f.is_demo} /></span>}
        actions={
          <>
            {canSubmit && <Button icon={<Send className="size-4" />} loading={review.isPending} onClick={() => review.mutate({ action: 'submit-review', text: '' })}>{t("Demander la vérification d'un expert")}</Button>}
            {canReview && <><Button onClick={() => setReviewing('validate')}>{t('Valider')}</Button><Button variant="secondary" onClick={() => setReviewing('reject')}>{t('Rejeter')}</Button></>}
            {canRation && <Button variant="secondary" icon={<Wheat className="size-4" />} onClick={() => navigate(`/rations?formule=${f.id}`)}>{t('Créer une ration')}</Button>}
            {writable && <Button variant="ghost" icon={<Trash2 className="size-4" />} onClick={() => setDeleting(true)}>{t('Supprimer')}</Button>}
          </>
        }
      />
      {review.isError && <Alert tone="error">{review.error.message}</Alert>}
      {f.status === 'PENDING_REVIEW' && f.review_due_at && (
        f.review_overdue ? (
          <Alert tone="warning" title={t('Délai de vérification dépassé')}>
            {t('Les administrateurs de la plateforme ont été relancés. Vous pouvez aussi inviter un autre nutritionniste (Paramètres → Membres) ou utiliser une ration type validée.')}
          </Alert>
        ) : (
          <p className="text-sm text-slate-600">
            {t('Vérification demandée le {{asked}} · réponse attendue avant le {{due}}.', { asked: formatDateTime(f.review_requested_at ?? null), due: formatDateTime(f.review_due_at) })}
          </p>
        )
      )}
      {f.mode === 'TEMPLATE' && f.template_name && (
        <p className="text-sm text-slate-600">
          {f.is_demo
            ? t('Issue de la ration type DEMO « {{name}} » : exemple fictif, jamais validé.', { name: f.template_name })
            : t('Issue de la ration type « {{name}} », validée par un expert pour ce cas.', { name: f.template_name })}
        </p>
      )}
      {canMakeTemplate && <SaveAsTemplate formula={f} />}
      {writable && f.items.length > 0 && rationProblem && !needsRecovery && (
        <p className="text-sm text-slate-600">{rationProblem}</p>
      )}
      <FormulaResult formula={f} />
      {needsRecovery && <RecoverySteps formula={f} writable={writable} />}

      <Modal open={reviewing !== null} title={reviewing === 'validate' ? t('Valider cette formule') : t('Rejeter cette formule')} onClose={() => setReviewing(null)}
        footer={<>
          <Button variant="secondary" onClick={() => setReviewing(null)}>{t('Annuler')}</Button>
          <Button variant={reviewing === 'reject' ? 'danger' : 'primary'} loading={review.isPending} disabled={reviewing === 'reject' && !comment.trim()}
            onClick={() => reviewing && review.mutate({ action: reviewing, text: comment.trim() })}>{t('Confirmer')}</Button>
        </>}>
        <label htmlFor="review-comment" className="mb-1.5 block text-sm font-medium text-slate-700">{t('Commentaire')} {reviewing === 'reject' && <span className="text-red-600">*</span>}</label>
        <textarea id="review-comment" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        {reviewing === 'validate' && <p className="mt-2 text-xs text-slate-500">{t("En validant, vous attestez avoir vérifié cette formule pour l'usage prévu.")}</p>}
      </Modal>
      <ConfirmDialog open={deleting} title={t('Supprimer cette formule ?')} danger confirmLabel={t('Supprimer')} loading={removal.isPending}
        message={<>{t('La formule et son détail de calcul seront supprimés.')}{removal.isError && <span className="mt-2 block text-red-600">{removal.error.message}</span>}</>}
        onConfirm={() => removal.mutate()} onCancel={() => setDeleting(false)} />
    </div>
  )
}
