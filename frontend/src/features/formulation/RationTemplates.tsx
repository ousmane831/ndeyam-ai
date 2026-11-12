import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BadgeCheck, Zap } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, EmptyState, Stamp } from '@/components/ui/Feedback'
import { Spinner } from '@/components/ui/Spinner'
import { useOnline } from '@/features/offline/connectivity'
import { ValidationBadge, WorkflowActions } from '@/features/reference/Workflow'
import { useRoles } from '@/hooks/useRoles'
import { ApiError } from '@/services/api'
import { templateService } from '@/services/formulas'
import type { RationTemplate } from '@/types/formula'
import { formatNumber } from '@/utils/format'
import { IngredientIcon } from './IngredientIcon'
import { plainName } from './rationText'

const errorText = (e: unknown, fallback: string) => (e instanceof ApiError ? [e.message, ...Object.values(e.fieldErrors).flat()].join(' ') : fallback)

/** Une ration type : à qui elle s'applique, ses aliments (part de la matière sèche) et son statut. */
export function TemplateSummary({ template }: { template: RationTemplate }) {
  const { t } = useTranslation()
  const profile = [template.category_name, template.physiological_stage_name, template.objective_name, template.season_name].filter(Boolean).map((x) => t(x!))
  return (
    <div className="space-y-2">
      <p className="text-sm text-slate-600">
        {profile.join(' · ')}{profile.length ? ' · ' : ''}
        {t('{{min}} à {{max}} kg', { min: formatNumber(template.weight_min_kg), max: formatNumber(template.weight_max_kg) })}
        {' · '}{t('{{dm}} kg de matière sèche par animal et par jour', { dm: formatNumber(template.dm_intake_kg_day, 3) })}
      </p>
      <ul className="flex flex-wrap gap-2">
        {template.items.map((i) => (
          <li key={i.ingredient} className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white py-1 pr-3 pl-1 text-sm">
            <IngredientIcon category={i.ingredient_category} />
            <span>{plainName(i.ingredient_name)}</span>
            <span className="font-semibold tabular-nums">{formatNumber(i.inclusion_pct_dm, 1)} %</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/**
 * Formule rapide : rations types validées applicables au lot choisi. Un toucher suffit, la ration est
 * utilisable tout de suite (pas d'attente d'un expert : il l'a déjà validée pour ce cas).
 */
export function MatchingTemplates({ farm, group, objective, season, isDemo }: { farm: number; group: number; objective: number | null; season: number | null; isDemo: boolean }) {
  const { t } = useTranslation()
  const online = useOnline()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const matching = useQuery({
    queryKey: ['templates', 'matching', farm, group, objective, season],
    queryFn: () => templateService.matching({ farm, group, objective, season }),
  })
  const apply = useMutation({
    mutationFn: (id: number) => templateService.apply(id, { farm, group, objective, season }),
    onSuccess: (formula) => navigate(`/formulation/${formula.id}`),
    onError: (e) => setError(errorText(e, t('Application impossible.'))),
  })
  const list = matching.data ?? []
  if (!online || list.length === 0) return null
  return (
    <section aria-labelledby="templates-title" className="rounded-md border-2 border-acacia-600 bg-acacia-50 p-4">
      <h2 id="templates-title" className="flex items-center gap-2 font-display text-lg font-bold text-acacia-800">
        <BadgeCheck className="size-5" aria-hidden /> {t('Rations types pour ce lot')}
      </h2>
      <p className="mt-1 text-sm text-acacia-800">
        {isDemo
          ? t('Exemples DEMO : en conditions réelles, une ration type est validée une fois par un expert, puis utilisable tout de suite.')
          : t('Validées par un expert pour ce cas : utilisables tout de suite, sans attendre une vérification.')}
      </p>
      {error && <Alert tone="error" className="mt-3">{error}</Alert>}
      <ul className="mt-3 space-y-3">
        {list.map((tpl) => (
          <li key={tpl.id} className="rounded-md border border-acacia-200 bg-white p-4">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <p className="font-semibold text-slate-900">{tpl.name}</p>
              {tpl.is_demo ? <Stamp tone="demo">DEMO</Stamp> : <Stamp tone="ok">{t('Validée')}</Stamp>}
            </div>
            <TemplateSummary template={tpl} />
            <Button className="mt-3 w-full sm:w-auto" icon={<Zap className="size-4" />} loading={apply.isPending && apply.variables === tpl.id} onClick={() => apply.mutate(tpl.id)}>
              {t('Utiliser cette ration type')}
            </Button>
          </li>
        ))}
      </ul>
    </section>
  )
}

/** Onglet « Rations types » : liste ; les experts les valident (circuit habituel, source obligatoire). */
export function TemplateList() {
  const { t } = useTranslation()
  const { isReviewer } = useRoles()
  const queryClient = useQueryClient()
  const templates = useQuery({ queryKey: ['templates', 'list'], queryFn: templateService.list })
  if (templates.isPending) return <Spinner />
  if (templates.isError) return <Alert tone="error">{templates.error.message}</Alert>
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        {t("Une ration type est validée une fois par un nutritionniste ou zootechnicien pour un cas courant (espèce, stade, objectif, saison, tranche de poids). L'éleveur l'applique ensuite immédiatement : seuls les quantités et le coût sont recalculés avec ses aliments et ses prix.")}
      </p>
      {isReviewer && <p className="text-sm text-slate-600">{t('Pour en créer une : ouvrez une formule validée et choisissez « Enregistrer comme ration type ».')}</p>}
      {templates.data.length === 0 ? (
        <EmptyState title={t('Aucune ration type disponible pour le moment')} />
      ) : (
        <ul className="space-y-3">
          {templates.data.map((tpl) => (
            <li key={tpl.id} className="rounded-md border border-slate-200 bg-white p-4">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold text-slate-900">{tpl.name}</p>
                <ValidationBadge status={tpl.status} isDemo={tpl.is_demo} />
              </div>
              <TemplateSummary template={tpl} />
              {tpl.conditions && <p className="mt-2 text-sm text-slate-600">{tpl.conditions}</p>}
              {isReviewer && (
                <div className="mt-3">
                  <WorkflowActions status={tpl.status} canSubmit isReviewer
                    onAction={async (action, comment) => { await templateService.transition(tpl.id, action, comment); await queryClient.invalidateQueries({ queryKey: ['templates'] }) }} />
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
