import { ArrowLeft, ArrowRight, CloudOff } from 'lucide-react'
import { Link, useParams } from 'react-router'
import { Alert, Badge, Card } from '@/components/ui/Feedback'
import { PageHeader } from '@/components/ui/Layout'
import { RationCard } from '@/features/formulation/RationCard'
import { useOfflineFormula, type OfflineFormula } from '@/features/offline/offlineResults'
import { useOutbox } from '@/features/offline/outbox'
import type { Formula } from '@/types/formula'
import { formatDateTime, formatNumber } from '@/utils/format'

const CHECK = { ok: ['Respecté', 'brand'], below: ['Insuffisant', 'danger'], above: ['Dépassé', 'danger'], unknown: ['Non vérifiable', 'warning'] } as const

/** Forme « formule » attendue par la carte ration (aucune valeur ajoutée : tout vient du calcul hors ligne). */
function asFormula(f: OfflineFormula): Formula {
  const r = f.result
  const str = (v: number | null) => (v === null ? null : String(v))
  return {
    id: 0, farm: f.farm, name: f.name, species: 0, reference: null, mode: r.mode, mode_label: '', status: 'ESTIMATED', status_label: 'Estimation hors ligne',
    is_demo: f.isDemo, animal: null, group: null, animal_weight_kg: null, animal_age_months: null, physiological_stage: null, objective: null,
    dm_intake_kg_day: str(r.dm_intake_kg_day), as_fed_kg_day: str(r.as_fed_kg_day), cost_per_day: str(r.cost_per_day), cost_per_kg_as_fed: str(r.cost_per_kg_as_fed),
    currency: r.currency,
    items: r.items.map((i, k) => ({
      id: k + 1, ingredient: i.ingredient_id, ingredient_name: i.name, ingredient_category: f.categories?.[i.ingredient_id] ?? null,
      inclusion_pct_dm: String(i.inclusion_pct_dm), inclusion_pct_as_fed: null, quantity_dm_kg: String(i.quantity_dm_kg), quantity_as_fed_kg: String(i.quantity_as_fed_kg),
      price_per_kg_as_fed: str(i.price_per_kg_as_fed), cost_per_day: str(i.cost_per_day),
    })),
    result_snapshot: { profile: { head_count: f.headCount } }, warnings: [], solver_status: '', engine_version: '', validated_by_email: null, validated_at: null,
    review_comment: '', notes: '', created_at: f.createdAt,
  }
}

/** Résultat d'un calcul fait sans connexion : provisoire, recalculé et enregistré par le serveur au retour du réseau. */
export function OfflineFormulaPage() {
  const { id } = useParams()
  const f = useOfflineFormula(id)
  const pending = useOutbox().some((e) => e.kind === 'formula' && e.localResultId === id)
  if (!f) return <Alert tone="error">Ce calcul hors ligne n'est plus sur cet appareil.</Alert>
  const r = f.result
  return (
    <div className="space-y-6">
      <Link to="/formulation?onglet=formules" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"><ArrowLeft className="size-4" /> Formules</Link>
      <PageHeader title={f.name} description={<span className="inline-flex items-center gap-2"><CloudOff className="size-4" aria-hidden /> Calcul hors ligne · {formatDateTime(f.createdAt)}</span>} />

      {f.serverFormulaId ? (
        <Alert tone="success" title="Recalculée et enregistrée par le serveur">
          <Link to={`/formulation/${f.serverFormulaId}`} className="inline-flex items-center gap-1 font-semibold underline">Voir la formule officielle <ArrowRight className="size-4" aria-hidden /></Link>
          {' '}C'est elle qui fait foi, et c'est d'elle que l'on demande la vérification d'un expert.
        </Alert>
      ) : (
        <Alert tone="info" title="Résultat provisoire, calculé sur cet appareil">
          Mêmes données et mêmes règles que le calcul en ligne. {pending ? 'Il sera recalculé et enregistré par le serveur dès le retour du réseau ; vous pourrez alors demander la vérification d’un expert.' : ''}
        </Alert>
      )}

      {r.status === 'REFUSED' && <Alert tone="error" title="Calcul refusé : données insuffisantes"><ul className="list-disc space-y-1 pl-5">{r.refusal_reasons.map((x) => <li key={x}>{x}</li>)}</ul></Alert>}
      {r.status === 'INFEASIBLE' && <Alert tone="warning" title="Aucune ration ne respecte toutes les contraintes">{r.refusal_reasons[0] ?? 'Le recalcul indépendant révèle une contrainte non respectée.'}</Alert>}
      {r.items.length > 0 && <RationCard formula={asFormula(f)} />}

      {r.checks.length > 0 && (
        <Card title="Vérification des besoins (recalcul indépendant)">
          <ul className="divide-y divide-slate-100 text-sm">
            {r.checks.map((c) => (
              <li key={c.label} className="flex flex-wrap items-center justify-between gap-2 py-2 first:pt-0">
                <span className="text-slate-700">{c.label}</span>
                <span className="flex items-center gap-2">
                  <span className="text-slate-500">{c.value === null ? '—' : formatNumber(c.value, 3)} {c.unit}</span>
                  <Badge tone={CHECK[c.status][1]}>{CHECK[c.status][0]}</Badge>
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
      {f.notes.length > 0 && (
        <Card title="Profil et avertissements">
          <p className="mb-2 text-sm text-slate-600">Référence : {f.referenceName || 'aucune'}</p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">{f.notes.map((n) => <li key={n}>{n}</li>)}</ul>
        </Card>
      )}
    </div>
  )
}
