import clsx from 'clsx'
import { Alert, Badge, Card } from '@/components/ui/Feedback'
import { td, th } from '@/components/ui/Layout'
import type { Formula, NutrientSupply } from '@/types/formula'
import { formatMoney, formatNumber } from '@/utils/format'

const CHECK = {
  ok: { label: 'Respecté', tone: 'brand' },
  below: { label: 'Insuffisant', tone: 'danger' },
  above: { label: 'Dépassé', tone: 'danger' },
  unknown: { label: 'Non vérifiable', tone: 'warning' },
} as const

function bounds(min: number | null, target: number | null, max: number | null) {
  const parts = []
  if (min !== null) parts.push(`min ${formatNumber(min, 3)}`)
  if (target !== null) parts.push(`cible ${formatNumber(target, 3)}`)
  if (max !== null) parts.push(`max ${formatNumber(max, 3)}`)
  return parts.join(' · ') || '—'
}

export function StatusBanner({ formula }: { formula: Formula }) {
  const s = formula.result_snapshot
  switch (formula.status) {
    case 'REFUSED':
      return (
        <Alert tone="error" title="Calcul refusé : données insuffisantes">
          <ul className="list-disc space-y-1 pl-5">{(s.refusal_reasons ?? []).map((r) => <li key={r}>{r}</li>)}</ul>
        </Alert>
      )
    case 'INFEASIBLE':
      return (
        <Alert tone="warning" title="Aucune ration ne respecte toutes les contraintes">
          <p>{s.refusal_reasons?.[0]}</p>
          {s.infeasibility && s.infeasibility.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5">{s.infeasibility.map((d, i) => <li key={i}><strong>{d.constraint}</strong> : {d.explanation}</li>)}</ul>
          )}
          <p className="mt-2 text-xs">Ce diagnostic propose une explication possible (contraintes à relâcher), pas nécessairement la seule.</p>
        </Alert>
      )
    case 'VALIDATED':
      return <Alert tone="success" title="Formule vérifiée par un expert">Validée par {formula.validated_by_email ?? 'un expert'}{formula.review_comment ? ` : « ${formula.review_comment} »` : '.'}</Alert>
    case 'REJECTED':
      return <Alert tone="error" title="Formule rejetée par un expert">{formula.review_comment}</Alert>
    case 'PENDING_REVIEW':
      return <Alert tone="info" title="En attente de vérification">Un expert invité sur l'exploitation doit se prononcer. Ne l'utilisez pas comme recommandation d'ici là.</Alert>
    default:
      return (
        <Alert tone="warning" title={formula.mode === 'MANUAL' ? 'Analyse d’une ration saisie' : 'Estimation mathématique'}>
          {s.disclaimer ?? 'Résultat non vérifié par un expert.'}
        </Alert>
      )
  }
}

function NutrientTable({ nutrients }: { nutrients: NutrientSupply[] }) {
  if (nutrients.length === 0) return <p className="text-sm text-slate-500">Aucun apport calculable : aucune valeur validée pour les ingrédients utilisés.</p>
  return (
    <div className="-mx-5 overflow-x-auto">
      <table className="w-full">
        <thead className="border-y border-slate-200 bg-slate-50"><tr>
          <th className={th}>Nutriment</th><th className={th}>Apport / jour</th><th className={th}>Teneur / kg MS</th><th className={th}>Besoin de référence</th><th className={th}>Statut</th>
        </tr></thead>
        <tbody className="divide-y divide-slate-100">
          {nutrients.map((n) => (
            <tr key={n.code} className="align-top">
              <td className={td}><span className="font-medium">{n.code}</span>{n.system && <span className="ml-1 text-xs text-slate-500">({n.system})</span>}<p className="text-xs text-slate-500">{n.name}</p></td>
              <td className={td}>{n.daily_amount !== null ? `${formatNumber(n.daily_amount, 3)} ${n.daily_unit}` : <span className="text-slate-400">Inconnu</span>}</td>
              <td className={td}>{n.concentration_dm !== null ? `${formatNumber(n.concentration_dm, 3)} ${n.concentration_unit}` : '—'}</td>
              <td className={td}>{n.requirements?.length ? n.requirements.map((r, i) => <p key={i}>{bounds(r.min, r.target, r.max)} {r.unit}</p>) : '—'}</td>
              <td className={td}>
                {n.requirements?.map((r, i) => <Badge key={i} tone={CHECK[r.status].tone}>{CHECK[r.status].label}</Badge>)}
                {!n.complete && <p className="mt-1 text-xs text-amber-700">Valeur inconnue pour : {n.missing_for.join(', ')}</p>}
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
  const s = formula.result_snapshot
  const hasItems = formula.items.length > 0
  return (
    <div className="space-y-6">
      <StatusBanner formula={formula} />
      {formula.is_demo && <Alert tone="warning">Formule de DÉMONSTRATION calculée avec des données fictives.</Alert>}

      {hasItems && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ['Matière sèche / animal / j', formula.dm_intake_kg_day ? `${formatNumber(formula.dm_intake_kg_day, 3)} kg` : 'Inconnue'],
            ['Aliment brut / animal / j', formula.as_fed_kg_day ? `${formatNumber(formula.as_fed_kg_day, 3)} kg` : '—'],
            ['Coût / animal / j', formula.cost_per_day ? formatMoney(formula.cost_per_day, formula.currency) : 'Inconnu'],
            ['Coût / kg brut', formula.cost_per_kg_as_fed ? formatMoney(formula.cost_per_kg_as_fed, formula.currency) : 'Inconnu'],
          ].map(([label, value]) => (
            <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase">{label}</p>
              <p className="mt-1 text-lg font-semibold text-slate-900">{value}</p>
            </div>
          ))}
        </div>
      )}

      {hasItems && (
        <Card title="Composition de la ration">
          <div className="-mx-5 overflow-x-auto">
            <table className="w-full">
              <thead className="border-y border-slate-200 bg-slate-50"><tr>
                <th className={th}>Ingrédient</th><th className={th}>% MS</th><th className={th}>% brut</th><th className={th}>kg MS / j</th><th className={th}>kg brut / j</th><th className={th}>Prix / kg brut</th><th className={th}>Coût / j</th>
              </tr></thead>
              <tbody className="divide-y divide-slate-100">
                {formula.items.map((i) => (
                  <tr key={i.id}>
                    <td className={`${td} font-medium`}>{i.ingredient_name}</td>
                    <td className={td}>{i.inclusion_pct_dm !== null ? `${formatNumber(i.inclusion_pct_dm, 1)} %` : '—'}</td>
                    <td className={td}>{i.inclusion_pct_as_fed !== null ? `${formatNumber(i.inclusion_pct_as_fed, 1)} %` : '—'}</td>
                    <td className={td}>{formatNumber(i.quantity_dm_kg, 3)}</td>
                    <td className={td}>{formatNumber(i.quantity_as_fed_kg, 3)}</td>
                    <td className={td}>{formatMoney(i.price_per_kg_as_fed, formula.currency)}</td>
                    <td className={td}>{formatMoney(i.cost_per_day, formula.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {s.nutrients && (hasItems || formula.mode === 'MANUAL') && (
        <Card title="Apports estimés et comparaison aux besoins"><NutrientTable nutrients={s.nutrients} /></Card>
      )}

      {s.constraints && s.constraints.length > 0 && (
        <Card title="Vérification des contraintes (recalcul indépendant)">
          <ul className="divide-y divide-slate-100 text-sm">
            {s.constraints.map((c, i) => (
              <li key={i} className="flex flex-wrap items-center justify-between gap-2 py-2 first:pt-0">
                <span className="text-slate-700">{c.constraint}</span>
                <span className="flex items-center gap-2">
                  <span className="text-slate-500">{c.value !== null ? formatNumber(c.value, 3) : '—'} {c.unit} ({bounds(c.min, null, c.max)})</span>
                  <Badge tone={CHECK[c.status].tone}>{CHECK[c.status].label}</Badge>
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {(formula.warnings.length > 0 || (s.excluded_ingredients?.length ?? 0) > 0) && (
        <Card title="Avertissements et limites">
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">{formula.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </Card>
      )}

      <Card title="Traçabilité">
        <dl className={clsx('grid gap-4 text-sm sm:grid-cols-2')}>
          <div><dt className="text-xs font-medium text-slate-500 uppercase">Référence utilisée</dt><dd className="mt-1">{s.reference ? `${s.reference.name} (${s.reference.system})${s.reference.source ? ` — ${s.reference.source}` : ''}` : '—'}</dd></div>
          <div><dt className="text-xs font-medium text-slate-500 uppercase">Moteur</dt><dd className="mt-1">{formula.mode_label}{formula.engine_version ? ` · version ${formula.engine_version}` : ''}{formula.solver_status ? ` · solveur : ${formula.solver_status}` : ''}</dd></div>
          <div className="sm:col-span-2"><dt className="text-xs font-medium text-slate-500 uppercase">Sources des données</dt>
            <dd className="mt-1">{s.sources?.length ? <ul className="list-disc pl-5">{s.sources.map((x) => <li key={x}>{x}</li>)}</ul> : 'Aucune'}</dd></div>
        </dl>
      </Card>
    </div>
  )
}
