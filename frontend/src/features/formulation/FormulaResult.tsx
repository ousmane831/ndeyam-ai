import clsx from 'clsx'
import { useTranslation } from 'react-i18next'
import { Alert, Badge, Card } from '@/components/ui/Feedback'
import { tk } from '@/i18n'
import { td, th } from '@/components/ui/Layout'
import type { Formula, NutrientSupply } from '@/types/formula'
import { formatMoney, formatNumber } from '@/utils/format'
import { RationCard } from './RationCard'

const CHECK = {
  ok: { label: tk('Respecté'), tone: 'brand' },
  below: { label: tk('Insuffisant'), tone: 'danger' },
  above: { label: tk('Dépassé'), tone: 'danger' },
  unknown: { label: tk('Non vérifiable'), tone: 'warning' },
} as const

/** Tableau sur ordinateur, cartes étiquetées sur téléphone (un seul DOM : pas de doublon pour les lecteurs d'écran). */
const stack = {
  table: 'w-full max-sm:block',
  thead: 'border-y border-slate-200 bg-slate-50 max-sm:hidden',
  tbody: 'divide-y divide-slate-100 max-sm:block max-sm:border-t max-sm:border-slate-200',
  tr: 'max-sm:grid max-sm:grid-cols-2 max-sm:gap-x-4 max-sm:gap-y-2 max-sm:px-5 max-sm:py-3',
  title: 'max-sm:col-span-2 max-sm:p-0',
  cell: 'max-sm:p-0 max-sm:before:block max-sm:before:text-xs max-sm:before:font-medium max-sm:before:text-slate-500 max-sm:before:content-[attr(data-label)]',
}

type Translate = (key: string, options?: Record<string, unknown>) => string

function bounds(t: Translate, min: number | null, target: number | null, max: number | null) {
  const parts = []
  if (min !== null) parts.push(t('min {{value}}', { value: formatNumber(min, 3) }))
  if (target !== null) parts.push(t('cible {{value}}', { value: formatNumber(target, 3) }))
  if (max !== null) parts.push(t('max {{value}}', { value: formatNumber(max, 3) }))
  return parts.join(' · ') || '—'
}

export function StatusBanner({ formula }: { formula: Formula }) {
  const { t } = useTranslation()
  const s = formula.result_snapshot
  switch (formula.status) {
    case 'REFUSED':
      return (
        <Alert tone="error" title={t('Calcul refusé : données insuffisantes')}>
          <ul className="list-disc space-y-1 pl-5">{(s.refusal_reasons ?? []).map((r) => <li key={r}>{r}</li>)}</ul>
        </Alert>
      )
    case 'INFEASIBLE':
      return (
        <Alert tone="warning" title={t('Aucune ration ne respecte toutes les contraintes')}>
          <p>{s.refusal_reasons?.[0]}</p>
          {s.infeasibility && s.infeasibility.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5">{s.infeasibility.map((d, i) => <li key={i}><strong>{d.constraint}</strong> : {d.explanation}</li>)}</ul>
          )}
          <p className="mt-2 text-xs">{t('Ce diagnostic propose une explication possible (contraintes à relâcher), pas nécessairement la seule.')}</p>
        </Alert>
      )
    case 'VALIDATED':
      return (
        <Alert tone="success" title={t('Formule vérifiée par un expert')}>
          {formula.review_comment
            ? t('Validée par {{who}} : « {{comment}} »', { who: formula.validated_by_email ?? t('un expert'), comment: formula.review_comment })
            : t('Validée par {{who}}.', { who: formula.validated_by_email ?? t('un expert') })}
        </Alert>
      )
    case 'REJECTED':
      return <Alert tone="error" title={t('Formule rejetée par un expert')}>{formula.review_comment}</Alert>
    case 'PENDING_REVIEW':
      return <Alert tone="info" title={t('En attente de vérification')}>{t("Un expert invité sur l'exploitation doit se prononcer. Ne l'utilisez pas comme recommandation d'ici là.")}</Alert>
    default:
      return (
        <Alert tone="warning" title={formula.mode === 'MANUAL' ? t('Analyse d’une ration saisie') : t('Estimation mathématique')}>
          {s.disclaimer ?? t('Résultat non vérifié par un expert.')}
        </Alert>
      )
  }
}

function NutrientTable({ nutrients }: { nutrients: NutrientSupply[] }) {
  const { t } = useTranslation()
  if (nutrients.length === 0) return <p className="text-sm text-slate-500">{t('Aucun apport calculable : aucune valeur validée pour les ingrédients utilisés.')}</p>
  return (
    <div className="-mx-5 sm:overflow-x-auto">
      <table className={stack.table}>
        <thead className={stack.thead}><tr>
          <th className={th}>{t('Nutriment')}</th><th className={th}>{t('Apport / jour')}</th><th className={th}>{t('Teneur / kg MS')}</th><th className={th}>{t('Besoin de référence')}</th><th className={th}>{t('Statut')}</th>
        </tr></thead>
        <tbody className={stack.tbody}>
          {nutrients.map((n) => (
            <tr key={n.code} className={clsx('align-top', stack.tr)}>
              <td className={clsx(td, stack.title)}><span className="font-medium">{n.code}</span>{n.system && <span className="ml-1 text-xs text-slate-500">({n.system})</span>}<p className="text-xs text-slate-500">{n.name}</p></td>
              <td className={clsx(td, stack.cell)} data-label={t('Apport / jour')}>{n.daily_amount !== null ? `${formatNumber(n.daily_amount, 3)} ${n.daily_unit}` : <span className="text-slate-500">{t('Inconnu')}</span>}</td>
              <td className={clsx(td, stack.cell)} data-label={t('Teneur / kg MS')}>{n.concentration_dm !== null ? `${formatNumber(n.concentration_dm, 3)} ${n.concentration_unit}` : '—'}</td>
              <td className={clsx(td, stack.cell)} data-label={t('Besoin de référence')}>{n.requirements?.length ? n.requirements.map((r, i) => <p key={i}>{bounds(t, r.min, r.target, r.max)} {r.unit}</p>) : '—'}</td>
              <td className={clsx(td, stack.cell)} data-label={t('Statut')}>
                {n.requirements?.map((r, i) => <Badge key={i} tone={CHECK[r.status].tone}>{t(CHECK[r.status].label)}</Badge>)}
                {!n.complete && <p className="mt-1 text-xs text-mil-700">{t('Valeur inconnue pour : {{names}}', { names: n.missing_for.join(', ') })}</p>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Présentation complète d'une formule (calculée ou saisie), sans aucune donnée ajoutée côté interface. */
export function FormulaResult({ formula }: { formula: Formula }) {
  const { t } = useTranslation()
  const s = formula.result_snapshot
  const hasItems = formula.items.length > 0
  return (
    <div className="space-y-6">
      <StatusBanner formula={formula} />
      {formula.is_demo && <Alert tone="warning">{t('Formule de DÉMONSTRATION calculée avec des données fictives.')}</Alert>}

      {hasItems && <RationCard formula={formula} />}

      {hasItems && (
        <h2 className="pt-2 font-display text-lg font-bold text-brand-900">{t('Détail du calcul (par animal)')}</h2>
      )}
      {hasItems && (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          {[
            [t('Matière sèche / animal / j'), formula.dm_intake_kg_day ? `${formatNumber(formula.dm_intake_kg_day, 3)} kg` : t('Inconnue')],
            [t('Aliment brut / animal / j'), formula.as_fed_kg_day ? `${formatNumber(formula.as_fed_kg_day, 3)} kg` : '—'],
            [t('Coût / animal / j'), formula.cost_per_day ? formatMoney(formula.cost_per_day, formula.currency) : t('Inconnu')],
            [t('Coût / kg brut'), formula.cost_per_kg_as_fed ? formatMoney(formula.cost_per_kg_as_fed, formula.currency) : t('Inconnu')],
          ].map(([label, value]) => (
            <div key={label} className="min-w-0 rounded-md border border-slate-200 bg-white p-3 sm:p-4">
              <p className="text-xs font-medium text-slate-500">{label}</p>
              <p className="mt-1 font-display text-lg font-bold text-brand-900 tabular-nums sm:text-xl">{value}</p>
            </div>
          ))}
        </div>
      )}

      {hasItems && (
        <Card title={t('Composition de la ration')}>
          <p className="mb-3 text-sm text-slate-500 sm:hidden">{t('Quantités par animal et par jour.')}</p>
          <div className="-mx-5 sm:overflow-x-auto">
            <table className={stack.table}>
              <thead className={stack.thead}><tr>
                <th className={th}>{t('Ingrédient')}</th><th className={th}>{t('% MS')}</th><th className={th}>{t('% brut')}</th><th className={th}>{t('kg MS / j')}</th><th className={th}>{t('kg brut / j')}</th><th className={th}>{t('Prix / kg brut')}</th><th className={th}>{t('Coût / j')}</th>
              </tr></thead>
              <tbody className={stack.tbody}>
                {formula.items.map((i) => (
                  <tr key={i.id} className={stack.tr}>
                    <td className={clsx(td, stack.title, 'font-medium')}>{i.ingredient_name}</td>
                    <td className={clsx(td, stack.cell, 'max-sm:order-3')} data-label={t('% de la MS')}>{i.inclusion_pct_dm !== null ? `${formatNumber(i.inclusion_pct_dm, 1)} %` : '—'}</td>
                    <td className={clsx(td, stack.cell, 'max-sm:hidden')} data-label={t('% du brut')}>{i.inclusion_pct_as_fed !== null ? `${formatNumber(i.inclusion_pct_as_fed, 1)} %` : '—'}</td>
                    <td className={clsx(td, stack.cell, 'max-sm:order-4')} data-label={t('kg MS / jour')}>{formatNumber(i.quantity_dm_kg, 3)}</td>
                    <td className={clsx(td, stack.cell, 'max-sm:order-1 max-sm:font-display max-sm:text-lg max-sm:font-bold max-sm:text-brand-900')} data-label={t('À distribuer (kg brut / jour)')}>{formatNumber(i.quantity_as_fed_kg, 3)}</td>
                    <td className={clsx(td, stack.cell, 'max-sm:order-5')} data-label={t('Prix / kg brut')}>{formatMoney(i.price_per_kg_as_fed, formula.currency)}</td>
                    <td className={clsx(td, stack.cell, 'max-sm:order-2')} data-label={t('Coût / jour')}>{formatMoney(i.cost_per_day, formula.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {s.nutrients && (hasItems || formula.mode === 'MANUAL') && (
        <Card title={t('Apports estimés et comparaison aux besoins')}><NutrientTable nutrients={s.nutrients} /></Card>
      )}

      {s.constraints && s.constraints.length > 0 && (
        <Card title={t('Vérification des contraintes (recalcul indépendant)')}>
          <ul className="divide-y divide-slate-100 text-sm">
            {s.constraints.map((c, i) => (
              <li key={i} className="flex flex-wrap items-center justify-between gap-2 py-2 first:pt-0">
                <span className="text-slate-700">{c.constraint}</span>
                <span className="flex items-center gap-2">
                  <span className="text-slate-500">{c.value !== null ? formatNumber(c.value, 3) : '—'} {c.unit} ({bounds(t, c.min, null, c.max)})</span>
                  <Badge tone={CHECK[c.status].tone}>{t(CHECK[c.status].label)}</Badge>
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {(formula.warnings.length > 0 || (s.excluded_ingredients?.length ?? 0) > 0) && (
        <Card title={t('Avertissements et limites')}>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">{formula.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </Card>
      )}

      <Card title={t('Traçabilité')}>
        <dl className={clsx('grid gap-4 text-sm sm:grid-cols-2')}>
          <div><dt className="text-xs font-medium text-slate-500">{t('Référence utilisée')}</dt><dd className="mt-1">{s.reference ? `${s.reference.name} (${s.reference.system})${s.reference.source ? ` — ${s.reference.source}` : ''}` : '—'}</dd></div>
          <div className="sm:col-span-2"><dt className="text-xs font-medium text-slate-500">{t('Sources des données')}</dt>
            <dd className="mt-1">{s.sources?.length ? <ul className="list-disc pl-5">{s.sources.map((x) => <li key={x}>{x}</li>)}</ul> : t('Aucune')}</dd></div>
        </dl>
        <details className="mt-4 text-sm text-slate-600">
          <summary className="cursor-pointer font-medium text-slate-700">{t('Détails techniques')}</summary>
          <p className="mt-2">
            {t('Calcul : {{mode}}', { mode: t(formula.mode_label) })}
            {formula.engine_version ? t(' · moteur version {{version}}', { version: formula.engine_version }) : ''}
            {formula.solver_status ? t(' · résolution : {{status}}', { status: formula.solver_status }) : ''}.
          </p>
        </details>
      </Card>
    </div>
  )
}
