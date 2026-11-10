import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { Calculator, ChevronDown } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, Card } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { Spinner } from '@/components/ui/Spinner'
import { tk } from '@/i18n'
import { useFarm } from '@/hooks/useFarm'
import { ApiError } from '@/services/api'
import { animalService, groupService, nomenclatureService } from '@/services/animals'
import { formulaService } from '@/services/formulas'
import { ingredientService, nutritionService, priceService, referenceService } from '@/services/nutrition'
import type { Formula } from '@/types/formula'
import type { Ingredient, IngredientPrice } from '@/types/nutrition'
import { formatMoney } from '@/utils/format'
import { buildCalculationPayload, type IngredientChoice } from './payload'

const MODES = [
  { value: 'ECONOMIC', label: tk('Économique'), help: tk('Coût minimal en respectant les besoins et contraintes validés.') },
  { value: 'BALANCED', label: tk('Équilibré'), help: tk('Au plus près des cibles fixées par les experts ; le coût est un critère secondaire.') },
] as const

const EMPTY_CHOICE: IngredientChoice = { selected: false, price: '', available: '' }
const priceInput =
  'block w-full rounded-md border border-slate-300 px-2.5 py-2 text-sm tabular-nums disabled:bg-slate-50 disabled:text-slate-500 sm:py-1.5'

/** Une ligne d'ingrédient : grille sur ordinateur, carte empilée sur téléphone (jamais de défilement horizontal). */
function IngredientRow({ ingredient, choice, lastPrice, onChange }: {
  ingredient: Ingredient
  choice: IngredientChoice
  lastPrice?: IngredientPrice
  onChange: (patch: Partial<IngredientChoice>) => void
}) {
  const { t } = useTranslation()
  const id = `ing-${ingredient.id}`
  return (
    <li className={clsx('grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2 px-5 py-3 sm:grid-cols-[auto_minmax(0,1fr)_7.5rem_8rem_8rem]', choice.selected && 'bg-brand-50/50')}>
      <input id={id} type="checkbox" aria-label={t('Utiliser {{name}}', { name: ingredient.name })} checked={choice.selected}
        onChange={(e) => onChange({ selected: e.target.checked })} className="size-5" />
      <label htmlFor={id} className="min-w-0 cursor-pointer">
        <span className="font-medium text-slate-800">{ingredient.name}</span>
        <span className="ml-2 inline-flex flex-wrap gap-1 align-middle">
          {ingredient.is_demo && <Badge tone="demo">DEMO</Badge>}
        </span>
      </label>
      <p className="col-start-2 text-sm text-slate-500 tabular-nums sm:col-start-auto sm:text-slate-700">
        <span className="sm:hidden">{t('Dernier prix : ')}</span>
        {lastPrice ? formatMoney(lastPrice.price_per_kg_as_fed, lastPrice.currency) : t('aucun')}
      </p>
      <div className={clsx('col-start-2 grid grid-cols-2 gap-3 sm:col-span-2 sm:col-start-auto', !choice.selected && 'max-sm:hidden')}>
        <label className="text-xs text-slate-500 sm:sr-only">
          {t('Prix (FCFA / kg brut)')}
          <input aria-label={t('Prix de {{name}}', { name: ingredient.name })} inputMode="decimal" disabled={!choice.selected} value={choice.price}
            placeholder={lastPrice ? t('dernier prix') : ''} onChange={(e) => onChange({ price: e.target.value })} className={clsx(priceInput, 'mt-1 sm:mt-0')} />
        </label>
        <label className="text-xs text-slate-500 sm:sr-only">
          {t('Stock (kg brut)')}
          <input aria-label={t('Stock de {{name}}', { name: ingredient.name })} inputMode="decimal" disabled={!choice.selected} value={choice.available}
            onChange={(e) => onChange({ available: e.target.value })} className={clsx(priceInput, 'mt-1 sm:mt-0')} />
        </label>
      </div>
    </li>
  )
}

type Profile = { animal: string; group: string; species: string; category: string; stage: string; objective: string; weight: string; age: string; reference: string; animals: string; days: string }
const EMPTY_PROFILE: Profile = { animal: '', group: '', species: '', category: '', stage: '', objective: '', weight: '', age: '', reference: '', animals: '', days: '' }

function initialFrom(f: Formula | undefined, t: (key: string, options?: Record<string, unknown>) => string) {
  if (!f) return null
  const profile = (f.result_snapshot.profile ?? {}) as Record<string, unknown>
  const str = (v: unknown) => (v === null || v === undefined ? '' : String(v))
  const ids = [...f.items.map((i) => i.ingredient), ...(f.result_snapshot.excluded_ingredients ?? []).map((e) => e.ingredient_id)]
  return {
    farm: f.farm,
    name: t('{{name}} (révisée)', { name: f.name }),
    mode: f.mode === 'BALANCED' ? ('BALANCED' as const) : ('ECONOMIC' as const),
    target: f.animal ? ('animal' as const) : f.group ? ('group' as const) : ('profile' as const),
    profile: {
      ...EMPTY_PROFILE,
      animal: str(f.animal), group: str(f.group), species: str(f.species), category: str(profile.category),
      stage: str(f.physiological_stage), objective: str(f.objective),
      weight: f.animal ? '' : str(f.animal_weight_kg), age: f.animal ? '' : str(f.animal_age_months), reference: str(f.reference),
    },
    choices: Object.fromEntries(ids.map((id) => [id, { ...EMPTY_CHOICE, selected: true }])) as Record<number, IngredientChoice>,
  }
}

/** Charge la formule d'origine si l'on reprend un calcul (?depuis=<id>), puis affiche le formulaire. */
export function CalculationForm() {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const fromId = Number(params.get('depuis')) || null
  const source = useQuery({ queryKey: ['formula', fromId], queryFn: () => formulaService.get(fromId!), enabled: fromId !== null })
  if (fromId !== null && source.isPending) return <Spinner label={t('Reprise de la formule…')} />
  return <CalculationFormBody key={source.data?.id ?? 'new'} source={source.data} />
}

function CalculationFormBody({ source }: { source?: Formula }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { writableFarms, defaultWritableFarmId, farms } = useFarm()
  const [initial] = useState(() => initialFrom(source, t))
  const [farmId, setFarmId] = useState<number | null>(initial?.farm ?? defaultWritableFarmId)
  const farm = farms.find((f) => f.id === farmId)
  const [name, setName] = useState(initial?.name ?? '')
  const [mode, setMode] = useState<'ECONOMIC' | 'BALANCED'>(initial?.mode ?? 'ECONOMIC')
  const [target, setTarget] = useState<'animal' | 'group' | 'profile'>(initial?.target ?? 'profile')
  const [p, setP] = useState<Profile>(initial?.profile ?? EMPTY_PROFILE)
  const [choices, setChoices] = useState<Record<number, IngredientChoice>>(initial?.choices ?? {})
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const species = useQuery({ queryKey: ['species'], queryFn: nomenclatureService.species, staleTime: Infinity })
  const speciesId = p.species ? Number(p.species) : species.data?.length === 1 ? species.data[0].id : undefined
  const categories = useQuery({ queryKey: ['categories', speciesId], queryFn: () => nomenclatureService.categories(speciesId), enabled: Boolean(speciesId) })
  const stages = useQuery({ queryKey: ['stages', speciesId], queryFn: () => nomenclatureService.stages(speciesId), enabled: Boolean(speciesId) })
  const objectives = useQuery({ queryKey: ['objectives'], queryFn: nutritionService.objectives, staleTime: Infinity })
  const animals = useQuery({ queryKey: ['animal-options', farmId], queryFn: () => animalService.options(farmId), enabled: farmId !== null })
  const groups = useQuery({ queryKey: ['groups', farmId], queryFn: () => groupService.list(farmId), enabled: farmId !== null })
  const references = useQuery({ queryKey: ['usable-references', speciesId, farm?.is_demo], queryFn: () => referenceService.usable(speciesId!, Boolean(farm?.is_demo)), enabled: Boolean(speciesId) })
  const ingredients = useQuery({ queryKey: ['ingredients-all'], queryFn: ingredientService.all })
  const prices = useQuery({ queryKey: ['prices', 'latest', farmId], queryFn: () => priceService.list({ farm: farmId, latest: true }), enabled: farmId !== null })

  const priceByIngredient = useMemo(() => new Map((prices.data ?? []).map((x) => [x.ingredient, x])), [prices.data])
  const demoFarm = Boolean(farm?.is_demo)
  // Une exploitation réelle n'utilise jamais de données DEMO (et inversement) : inutile de les proposer.
  const inScope = (ingredients.data ?? []).filter((i) => (i.farm === null || i.farm === farmId) && i.is_demo === demoFarm)
  const hiddenOtherWorld = (ingredients.data ?? []).filter((i) => (i.farm === null || i.farm === farmId) && i.is_demo !== demoFarm).length
  // Même règle que le moteur : sans matière sèche utilisable, l'ingrédient est exclu du calcul.
  const isReady = (i: Ingredient) => i.ready_for_engine ?? i.status === 'VALIDATED'
  const ready = inScope.filter(isReady)
  const others = inScope.filter((i) => !isReady(i))
  const choiceOf = (id: number) => choices[id] ?? EMPTY_CHOICE
  const selected = inScope.filter((i) => choiceOf(i.id).selected)
  const selectedCount = selected.length
  const needsHeadcount = selected.some((i) => choiceOf(i.id).available.trim())
  const risky = selected.filter((i) => !isReady(i))
  const unpriced = mode === 'ECONOMIC' ? selected.filter((i) => !choiceOf(i.id).price.trim() && !priceByIngredient.has(i.id)) : []
  const set = (k: keyof typeof p) => (e: { target: { value: string } }) => setP((s) => ({ ...s, [k]: e.target.value }))
  const choose = (id: number, patch: Partial<IngredientChoice>) => setChoices((c) => ({ ...c, [id]: { ...(c[id] ?? EMPTY_CHOICE), ...patch } }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (farmId === null) return setError(t('Choisissez une exploitation.'))
    if (!name.trim()) return setError(t('Donnez un nom à cette formule.'))
    if (target === 'animal' && !p.animal) return setError(t('Choisissez un animal.'))
    if (target === 'group' && !p.group) return setError(t('Choisissez un lot.'))
    if (selectedCount === 0) return setError(t('Sélectionnez au moins un ingrédient.'))
    if (needsHeadcount && (!p.animals || !p.days)) return setError(t('Indiquez le nombre d’animaux et la durée pour tenir compte des quantités disponibles.'))
    setBusy(true)
    try {
      const inScopeIds = new Set(inScope.map((i) => i.id))
      const scoped = Object.fromEntries(Object.entries(choices).filter(([id]) => inScopeIds.has(Number(id))))
      const payload = buildCalculationPayload({ farm: farmId, name, mode, target, ...p, species: p.species || String(speciesId ?? ''), choices: scoped })
      const { formula } = await formulaService.calculate(payload)
      if (formula) navigate(`/formulation/${formula.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? Object.values(err.fieldErrors).flat().join(' ') || err.message : t('Calcul impossible.'))
    } finally {
      setBusy(false)
    }
  }

  if (writableFarms.length === 0) return <Alert tone="info">{t("Le calcul de formules est réservé aux propriétaires et gestionnaires d'exploitation.")}</Alert>
  const opts = (items: { id: number; name: string }[] | undefined, empty: string) => [{ value: '', label: empty }, ...(items ?? []).map((i) => ({ value: String(i.id), label: i.name }))]
  // Libellés de nomenclature (espèces, catégories, stades, objectifs) : traduits à l'affichage.
  const named = (items: { id: number; name: string }[] | undefined) => items?.map((i) => ({ id: i.id, name: t(i.name) }))
  const row = (i: Ingredient) => (
    <IngredientRow key={i.id} ingredient={i} choice={choiceOf(i.id)} lastPrice={priceByIngredient.get(i.id)} onChange={(patch) => choose(i.id, patch)} />
  )

  return (
    <form onSubmit={submit} noValidate className="space-y-6">
      {error && <Alert tone="error">{error}</Alert>}
      {source && (
        <Alert tone="info" title={t('Reprise de « {{name}} »', { name: source.name })}>
          {t('Profil, référence et ingrédients sont repris. Complétez les données manquantes signalées, puis relancez le calcul : une nouvelle formule sera enregistrée.')}
        </Alert>
      )}
      {demoFarm && <Alert tone="warning" title={t('Exploitation de démonstration')}>{t('Le calcul utilisera uniquement des données DEMO : ne pas utiliser pour nourrir des animaux.')}</Alert>}

      <Card title={t('1. Formule')}>
        <div className="grid gap-4 sm:grid-cols-2">
          {writableFarms.length > 1 && (
            <SelectField label={t('Exploitation')} value={farmId ? String(farmId) : ''} onChange={(e) => { setFarmId(Number(e.target.value)); setChoices({}) }}
              options={writableFarms.map((f) => ({ value: String(f.id), label: f.name }))} />
          )}
          <TextField label={t('Nom de la formule')} required value={name} onChange={(e) => setName(e.target.value)} placeholder={t('ex. Embouche Tabaski — lot A')} />
        </div>
        <fieldset className="mt-4">
          <legend className="mb-2 text-sm font-medium text-slate-700">{t('Mode de calcul')}</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            {MODES.map((m) => (
              <label key={m.value} className={`flex cursor-pointer gap-3 rounded-md border p-3 ${mode === m.value ? 'border-brand-500 bg-brand-50' : 'border-slate-200'}`}>
                <input type="radio" name="mode" value={m.value} checked={mode === m.value} onChange={() => setMode(m.value)} className="mt-1 size-4" />
                <span><span className="block font-medium text-slate-800">{t(m.label)}</span><span className="text-sm text-slate-500">{t(m.help)}</span></span>
              </label>
            ))}
          </div>
        </fieldset>
      </Card>

      <Card title={t('2. Animaux concernés')}>
        <div className="space-y-4">
          <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
            {([['profile', t('Profil type')], ['animal', t('Un animal')], ['group', t('Un lot')]] as const).map(([v, l]) => (
              <label key={v} className="inline-flex min-h-10 cursor-pointer items-center gap-2"><input type="radio" name="target" checked={target === v} onChange={() => setTarget(v)} className="size-4" />{l}</label>
            ))}
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {target === 'animal' && (
              <SelectField label={t('Animal')} value={p.animal} onChange={set('animal')} hint={t('Espèce, race, catégorie, stade, poids et âge sont repris de sa fiche.')}
                options={opts(animals.data?.map((a) => ({ id: a.id, name: `${a.tag_number}${a.name ? ` — ${a.name}` : ''}` })), t('Choisir…'))} />
            )}
            {target === 'group' && <SelectField label={t('Lot')} value={p.group} onChange={set('group')} options={opts(groups.data?.results, t('Choisir…'))} />}
            {target !== 'animal' && species.data && species.data.length > 1 && <SelectField label={t('Espèce')} value={p.species} onChange={set('species')} options={opts(named(species.data), t('Choisir…'))} />}
            <SelectField label={t('Catégorie')} value={p.category} onChange={set('category')} options={opts(named(categories.data), target === 'animal' ? t('Celle de la fiche') : t('Non précisée'))} />
            <SelectField label={t('Stade physiologique')} value={p.stage} onChange={set('stage')} options={opts(named(stages.data), target === 'animal' ? t('Celui de la fiche') : t('Non précisé'))} />
            <SelectField label={t('Objectif')} value={p.objective} onChange={set('objective')} options={opts(named(objectives.data), t('Non précisé'))} />
            <TextField label={t('Poids (kg)')} inputMode="decimal" value={p.weight} onChange={set('weight')} placeholder={target === 'animal' ? t('Dernier poids de la fiche') : ''} />
            <TextField label={t('Âge (mois)')} inputMode="decimal" value={p.age} onChange={set('age')} />
          </div>
          <SelectField label={t('Référence nutritionnelle')} value={p.reference} onChange={set('reference')}
            hint={references.data?.length === 0 ? t('Aucune référence utilisable pour cette espèce : le calcul sera refusé tant qu’un expert n’en a pas validé une.') : t('Le choix automatique retient la référence validée la plus adaptée au profil.')}
            options={[{ value: '', label: t('Automatique') }, ...(references.data ?? []).map((r) => ({ value: String(r.id), label: `${r.name} (${r.system_code})` }))]} />
        </div>
      </Card>

      <Card title={t('3. Ingrédients disponibles ({{count}} sélectionné(s))', { count: selectedCount })}>
        {ingredients.isPending ? <Spinner /> : inScope.length === 0 ? (
          <p className="text-sm text-slate-500">{t('Aucun ingrédient disponible. Ajoutez-en depuis la page Ingrédients.')}</p>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-slate-500">
              {t('Cochez les ingrédients dont vous disposez. Le prix proposé est le dernier prix enregistré ; remplacez-le si besoin pour ce calcul.')}
            </p>
            <div className="-mx-5 border-y border-slate-200">
              <div className="hidden grid-cols-[auto_minmax(0,1fr)_7.5rem_8rem_8rem] gap-x-3 bg-slate-50 px-5 py-2.5 font-mono text-xs font-semibold tracking-[0.06em] text-slate-500 uppercase sm:grid" aria-hidden>
                <span className="w-5" /><span>{t('Ingrédient')}</span><span>{t('Dernier prix')}</span><span>{t('Prix du calcul')}</span><span>{t('Stock (kg brut)')}</span>
              </div>
              {ready.length > 0 ? (
                <ul className="divide-y divide-slate-100">{ready.map(row)}</ul>
              ) : (
                <p className="px-5 py-3 text-sm text-slate-500">{t("Aucun ingrédient n'a encore de matière sèche validée par un expert : le calcul sera refusé.")}</p>
              )}
              {others.length > 0 && (
                <details className="group border-t border-slate-200" open={ready.length === 0 || others.some((i) => choiceOf(i.id).selected)}>
                  <summary className="flex cursor-pointer list-none items-center gap-2 px-5 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50">
                    <ChevronDown className="size-4 transition-transform group-open:rotate-180" aria-hidden />
                    {t('Sans matière sèche validée ({{count}}) : exclus du calcul', { count: others.length })}
                  </summary>
                  <ul className="divide-y divide-slate-100 border-t border-slate-100">{others.map(row)}</ul>
                </details>
              )}
            </div>
            {hiddenOtherWorld > 0 && (
              <p className="text-xs text-slate-500">
                {demoFarm
                  ? t("{{count}} ingrédient(s) réel(s) masqué(s) : une exploitation DEMO n'utilise que des données DEMO.", { count: hiddenOtherWorld })
                  : t('{{count}} ingrédient(s) DEMO masqué(s) : ils ne sont jamais utilisés dans une exploitation réelle.', { count: hiddenOtherWorld })}
              </p>
            )}
            {needsHeadcount && (
              <div className="grid gap-4 sm:grid-cols-2">
                <TextField label={t("Nombre d'animaux nourris")} inputMode="numeric" value={p.animals} onChange={set('animals')} />
                <TextField label={t('Durée couverte par le stock (jours)')} inputMode="numeric" value={p.days} onChange={set('days')} />
              </div>
            )}
          </div>
        )}
      </Card>

      {(risky.length > 0 || unpriced.length > 0) && (
        <Alert tone="warning" title={t('Avant de calculer')}>
          <ul className="list-disc space-y-1 pl-5">
            {risky.length > 0 && <li>{t("{{names}} : matière sèche non validée, l'ingrédient sera exclu du calcul.", { names: risky.map((i) => i.name).join(', ') })}</li>}
            {unpriced.length > 0 && <li>{t("{{names}} : aucun prix connu ; en mode économique, l'ingrédient sera exclu. Saisissez un prix ou passez en mode équilibré.", { names: unpriced.map((i) => i.name).join(', ') })}</li>}
          </ul>
        </Alert>
      )}

      <div className="sticky bottom-0 -mx-4 border-t border-slate-200 bg-white/95 px-4 py-3 pr-24 sm:static sm:mx-0 sm:flex sm:items-center sm:justify-between sm:gap-4 sm:border-0 sm:bg-transparent sm:p-0">
        <p className="mb-2 text-sm text-slate-500 sm:mb-0">{t('Le résultat sera une estimation, à faire vérifier par un expert avant usage.')}</p>
        <Button type="submit" loading={busy} icon={<Calculator className="size-4" />} className="w-full sm:w-auto">{t('Calculer la formule')}</Button>
      </div>
    </form>
  )
}
