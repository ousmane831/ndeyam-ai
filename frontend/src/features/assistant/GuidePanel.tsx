import clsx from 'clsx'
import { ArrowRight, Bell, Calculator, ClipboardCheck, Scale, Wheat } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router'

const STEPS: { icon: ReactNode; title: string; text: string; to: string; action: string }[] = [
  {
    icon: <Scale className="size-5" />,
    title: 'Peser vos animaux',
    text: "Tout un lot en une séance depuis Suivi de croissance ; un seul animal depuis sa fiche, onglet Pesées. Le GMD se calcule tout seul.",
    to: '/suivi-croissance',
    action: 'Séance de pesée',
  },
  {
    icon: <Calculator className="size-5" />,
    title: 'Calculer une ration',
    text: "Cochez les ingrédients dont vous disposez et leur prix : le moteur cherche la ration qui respecte les besoins validés au meilleur coût.",
    to: '/formulation',
    action: 'Formuler',
  },
  {
    icon: <ClipboardCheck className="size-5" />,
    title: 'Faire valider',
    text: "Un calcul est une estimation. Demandez la vérification d'un expert : seule une formule validée peut devenir une ration.",
    to: '/formulation?onglet=formules',
    action: 'Mes formules',
  },
  {
    icon: <Wheat className="size-5" />,
    title: 'Suivre la distribution',
    text: "Enregistrez chaque distribution. La quantité consommée n'est jamais supposée : saisissez-la seulement si vous l'avez pesée.",
    to: '/rations',
    action: 'Rations',
  },
  {
    icon: <Bell className="size-5" />,
    title: 'Répondre aux alertes',
    text: 'Pesées en retard, fiches à compléter, formules en attente : elles apparaissent aussi en tête du tableau de bord.',
    to: '/alertes',
    action: 'Alertes',
  },
]

const GLOSSARY: [string, string][] = [
  ['MS (matière sèche)', "Ce qui reste d'un aliment sans son eau. Les besoins et les teneurs sont exprimés par kg de MS."],
  ['Brut', "L'aliment tel qu'il est distribué, avec son eau. Les prix et les quantités distribuées sont en kg brut."],
  ['GMD', 'Gain moyen quotidien : (poids final − poids initial) ÷ nombre de jours, en grammes par jour.'],
  ['UFL / UFV', "Unités fourragères : l'énergie apportée par l'aliment (système INRA)."],
  ['EM', 'Énergie métabolisable (système NRC).'],
  ['MAT', 'Matières azotées totales : les protéines brutes.'],
  ['PDI / PM', 'Protéines digestibles (INRA) ou métabolisables (NRC).'],
  ['CB, NDF, ADF', 'Les fibres de la ration (cellulose et ses fractions).'],
  ['Ca, P', 'Calcium et phosphore.'],
  ['Estimation', "Résultat du moteur, pas encore vérifié par un expert : il ne peut pas devenir une ration."],
  ['Référence', "Besoins documentés d'un type d'animal, avec leur source, validés par un expert."],
  ['DEMO', 'Donnée fictive de démonstration : jamais validée, jamais utilisée pour une exploitation réelle.'],
]

/** Contenu affiché par le bouton bélier quand l'assistant IA n'est pas activé. */
export function GuidePanel({ onNavigate, adminNote }: { onNavigate: () => void; adminNote: boolean }) {
  const [tab, setTab] = useState<'guide' | 'glossaire'>('guide')
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex gap-1 border-b border-slate-200 px-3" role="tablist" aria-label="Guide">
        {([['guide', 'Guide rapide'], ['glossaire', 'Glossaire']] as const).map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
            className={clsx('-mb-px min-h-11 border-b-2 px-3 text-sm font-semibold', tab === id ? 'border-mil-400 text-brand-800' : 'border-transparent text-slate-500 hover:text-slate-800')}>
            {label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto bg-slate-50 p-3">
        {tab === 'guide' ? (
          <ol className="space-y-2">
            {STEPS.map((s) => (
              <li key={s.title} className="rounded-md bg-white p-3 ring-1 ring-slate-200">
                <div className="flex gap-3">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-brand-50 text-brand-700">{s.icon}</span>
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">{s.title}</p>
                    <p className="mt-0.5 text-sm text-slate-600">{s.text}</p>
                    <Link to={s.to} onClick={onNavigate} className="mt-1.5 inline-flex min-h-9 items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">
                      {s.action} <ArrowRight className="size-4" aria-hidden />
                    </Link>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <dl className="divide-y divide-slate-200 rounded-md bg-white ring-1 ring-slate-200">
            {GLOSSARY.map(([term, def]) => (
              <div key={term} className="px-3 py-2.5">
                <dt className="font-semibold text-slate-900">{term}</dt>
                <dd className="mt-0.5 text-sm text-slate-600">{def}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
      <p className="border-t border-slate-200 bg-white px-4 py-2.5 text-[13px] leading-snug text-slate-600">
        L'assistant conversationnel n'est pas encore activé : ce guide le remplace.
        {adminNote && <> Pour l'activer, renseignez <code className="font-mono text-xs">LLM_PROVIDER</code> dans <code className="font-mono text-xs">backend/.env</code>.</>}
      </p>
    </div>
  )
}
