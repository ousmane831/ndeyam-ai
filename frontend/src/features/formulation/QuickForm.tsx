import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { Calculator, Check } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, Card } from '@/components/ui/Feedback'
import { SelectField } from '@/components/ui/Field'
import { Spinner } from '@/components/ui/Spinner'
import { useFarm } from '@/hooks/useFarm'
import { ApiError } from '@/services/api'
import { groupService } from '@/services/animals'
import { availabilityService, seasonService } from '@/services/seasons'
import { SeasonIcon } from '@/features/seasons/SeasonCalendar'
import { seasonTone } from '@/features/seasons/seasonStyle'
import { formulaService } from '@/services/formulas'
import { ingredientService, nutritionService, priceService } from '@/services/nutrition'
import type { CalculationPayload } from '@/types/formula'
import { formatMoney } from '@/utils/format'
import { isOnline } from '@/features/offline/connectivity'
import { saveOfflineFormula } from '@/features/offline/offlineResults'
import { isNetworkError, outbox } from '@/features/offline/outbox'
import { estimateForGroup } from '@/features/offline/estimate'
import { loadPack, type OfflinePack } from '@/features/offline/pack'
import type { Ingredient } from '@/types/nutrition'
import { IngredientIcon } from './IngredientIcon'
import { MatchingTemplates } from './RationTemplates'
import { plainName, quickFormulaName } from './rationText'

/** Derniers aliments cochés et objectif de chaque lot, mémorisés sur cet appareil (commodité, jamais indispensable). */
type Memory = { ingredients: number[]; objectives: Record<string, string> }
const memoryKey = (farm: number) => `ndeyam.formule-rapide.${farm}`
function recall(farm: number | null): Memory {
  const empty: Memory = { ingredients: [], objectives: {} }
  if (farm === null) return empty
  try {
    const raw = JSON.parse(localStorage.getItem(memoryKey(farm)) ?? 'null')
    return {
      ingredients: Array.isArray(raw?.ingredients) ? raw.ingredients.map(Number) : [],
      objectives: raw?.objectives && typeof raw.objectives === 'object' ? raw.objectives : {},
    }
  } catch {
    return empty
  }
}
function remember(farm: number, memory: Memory) {
  try {
    localStorage.setItem(memoryKey(farm), JSON.stringify(memory))
  } catch {
    /* stockage indisponible : sans conséquence */
  }
}

/** Lots, aliments et derniers prix tirés du paquet hors ligne (utilisés seulement sans données en mémoire). */
function packChoices(pack: OfflinePack | null, farm: number | null) {
  const empty = { lots: [] as { id: number; name: string; animals_count: number }[], ingredients: [] as Ingredient[], prices: new Map<number, { price_per_kg_as_fed: string; currency: string; seasonal?: boolean }>() }
  if (!pack) return empty
  const ready = new Set<number>()
  for (const ref of pack.references) {
    for (const i of ref.problem.ingredients) {
      if (i.dm_g_per_kg_as_fed) ready.add(i.id)
      if (i.price_per_kg_as_fed !== null && !empty.prices.has(i.id)) empty.prices.set(i.id, { price_per_kg_as_fed: String(i.price_per_kg_as_fed), currency: i.currency })
    }
  }
  empty.lots = pack.groups.filter((g) => g.head_count > 0).map((g) => ({ id: g.id, name: g.name, animals_count: g.head_count }))
  empty.ingredients = pack.ingredients.map((i) => ({ ...i, farm, is_demo: pack.is_demo, ready_for_engine: ready.has(i.id) }) as unknown as Ingredient)
  return empty
}

const tile = 'flex min-h-14 w-full items-center gap-3 rounded-md border-2 px-4 py-3 text-left transition-colors'

/**
 * Formule rapide : choisir un lot (son objectif est retenu), cocher ses aliments, calculer. Le profil (catégorie, stade, poids moyen)
 * est déduit des fiches du lot par le serveur ; la référence est choisie automatiquement ; mode économique.
 */
export function QuickForm() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { writableFarms, defaultWritableFarmId, farms } = useFarm()
  const [farmId, setFarmId] = useState<number | null>(defaultWritableFarmId)
  const [memory, setMemory] = useState(() => recall(defaultWritableFarmId))
  const [groupId, setGroupId] = useState<number | null>(null)
  const [objective, setObjective] = useState('')
  const [seasonChoice, setSeasonChoice] = useState<number | null>(null)
  const [picked, setPicked] = useState<Set<number>>(() => new Set(memory.ingredients))
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const farm = farms.find((f) => f.id === farmId)
  const demoFarm = Boolean(farm?.is_demo)

  const groups = useQuery({ queryKey: ['groups', farmId], queryFn: () => groupService.list(farmId), enabled: farmId !== null })
  const objectives = useQuery({ queryKey: ['objectives'], queryFn: nutritionService.objectives, staleTime: Infinity })
  const ingredients = useQuery({ queryKey: ['ingredients-all'], queryFn: ingredientService.all })
  const prices = useQuery({ queryKey: ['prices', 'latest', farmId], queryFn: () => priceService.list({ farm: farmId, latest: true }), enabled: farmId !== null })
  // Saison du calcul : la saison en cours par défaut (prix habituels et disponibilité de la saison).
  const seasons = useQuery({ queryKey: ['seasons'], queryFn: seasonService.list, staleTime: Infinity })
  const currentSeason = useQuery({ queryKey: ['season-current', farmId], queryFn: () => seasonService.current(farmId) })
  const seasonId = seasonChoice ?? currentSeason.data?.season?.id ?? null
  const seasonalPrices = useQuery({ queryKey: ['prices', 'season', farmId, seasonId], queryFn: () => priceService.list({ farm: farmId, season: seasonId }), enabled: farmId !== null && seasonId !== null })
  const availability = useQuery({ queryKey: ['availability', farmId, seasonId], queryFn: () => availabilityService.list({ farm: farmId, season: seasonId }), enabled: farmId !== null && seasonId !== null })
  const levelOf = useMemo(() => new Map((availability.data ?? []).map((a) => [a.ingredient, a.level])), [availability.data])
  // Sans réseau ni données en mémoire, le paquet de calcul hors ligne fournit lots, aliments et prix.
  const pack = useMemo(() => (farmId !== null ? loadPack(farmId) : null), [farmId])
  const fromPack = useMemo(() => packChoices(pack, farmId), [pack, farmId])
  const priceOf = useMemo(() => {
    const map = new Map(prices.data ? prices.data.map((x) => [x.ingredient, { price_per_kg_as_fed: x.price_per_kg_as_fed, currency: x.currency, seasonal: false }]) : fromPack.prices)
    // Même règle que le serveur : le prix habituel déclaré pour la saison passe avant le dernier prix relevé.
    for (const p of [...(seasonalPrices.data ?? [])].filter((x) => x.season === seasonId).sort((a, b) => a.valid_from.localeCompare(b.valid_from))) {
      map.set(p.ingredient, { price_per_kg_as_fed: p.price_per_kg_as_fed, currency: p.currency, seasonal: true })
    }
    return map
  }, [prices.data, fromPack, seasonalPrices.data, seasonId])

  const lots = groups.data ? groups.data.results.filter((g) => g.animals_count > 0) : fromPack.lots
  const lotsLoading = groups.isPending && fromPack.lots.length === 0
  // Mêmes règles que le calcul détaillé : monde DEMO ou réel, et matière sèche utilisable par le moteur.
  const usable = (ingredients.data ?? fromPack.ingredients).filter((i) => (i.farm === null || i.farm === farmId) && i.is_demo === demoFarm)
  const ready = usable.filter((i) => i.ready_for_engine ?? i.status === 'VALIDATED')
  const notReady = usable.length - ready.length
  const chosen = ready.filter((i) => picked.has(i.id))
  const unpriced = chosen.filter((i) => !priceOf.has(i.id))
  const toggle = (id: number) => setPicked((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n })

  const submit = async () => {
    setError(null)
    if (farmId === null) return setError(t('Choisissez une exploitation.'))
    const group = lots.find((g) => g.id === groupId)
    if (!group) return setError(t('Choisissez le lot à nourrir.'))
    if (chosen.length === 0) return setError(t('Cochez au moins un aliment dont vous disposez.'))
    const payload: CalculationPayload = {
      farm: farmId,
      name: quickFormulaName(group.name),
      mode: 'ECONOMIC',
      group: group.id,
      objective: objective ? Number(objective) : null,
      ...(seasonId !== null ? { season: seasonId } : {}),
      ingredients: chosen.map((i) => ({ ingredient: i.id })),
    }
    remember(farmId, { ingredients: chosen.map((i) => i.id), objectives: { ...memory.objectives, [group.id]: objective } })
    if (!isOnline()) return calculateOffline(payload, group.id)
    setBusy(true)
    try {
      const { formula } = await formulaService.calculate(payload)
      if (formula) navigate(`/formulation/${formula.id}`)
    } catch (err) {
      if (isNetworkError(err)) return calculateOffline(payload, group.id)
      setError(err instanceof ApiError ? Object.values(err.fieldErrors).flat().join(' ') || err.message : t('Calcul impossible.'))
    } finally {
      setBusy(false)
    }
  }

  /** Sans réseau : estimation sur l'appareil (paquet de calcul), recalcul officiel par le serveur au retour du réseau. */
  const calculateOffline = (payload: CalculationPayload, group: number) => {
    const current = farmId !== null ? loadPack(farmId) : null
    if (!current) {
      setError(t("Calcul hors ligne impossible : les données de calcul n'ont pas encore été téléchargées sur cet appareil. Ouvrez l'application une fois avec du réseau."))
      return
    }
    const estimate = estimateForGroup(current, group, payload.objective ?? null, payload.ingredients.map((i) => i.ingredient))
    if (!estimate) {
      setError(t("Ce lot n'est pas dans les données hors ligne de cet appareil. Reconnectez-vous pour les mettre à jour."))
      return
    }
    const id = `local-${Date.now()}`
    saveOfflineFormula({
      id, name: payload.name, farm: payload.farm, isDemo: current.is_demo, createdAt: new Date().toISOString(),
      referenceName: estimate.reference?.name ?? '', headCount: estimate.group.head_count, notes: estimate.notes, result: estimate.result,
      categories: Object.fromEntries(current.ingredients.map((i) => [i.id, i.category_code])),
    })
    outbox.add({ kind: 'formula', payload, label: t('Calcul « {{name}} »', { name: payload.name }), localResultId: id })
    navigate(`/formulation/hors-ligne/${id}`)
  }

  if (writableFarms.length === 0) return <Alert tone="info">{t("Le calcul de formules est réservé aux propriétaires et gestionnaires d'exploitation.")}</Alert>

  return (
    <div className="space-y-6">
      {error && <Alert tone="error">{error}</Alert>}
      {demoFarm && <Alert tone="warning" title={t('Exploitation de démonstration')}>{t('Le calcul utilisera uniquement des données DEMO : ne pas utiliser pour nourrir des animaux.')}</Alert>}
      {writableFarms.length > 1 && (
        <SelectField label={t('Exploitation')} value={farmId ? String(farmId) : ''}
          onChange={(e) => { const id = Number(e.target.value); const m = recall(id); setFarmId(id); setMemory(m); setGroupId(null); setObjective(''); setPicked(new Set(m.ingredients)) }}
          options={writableFarms.map((f) => ({ value: String(f.id), label: f.name }))} />
      )}

      <Card title={t('1. Quel lot nourrir ?')}>
        {lotsLoading ? <Spinner /> : lots.length === 0 ? (
          <p className="text-sm text-slate-600">{t('Aucun lot avec des animaux. Créez un lot dans')} <Link to="/troupeaux" className="font-semibold text-brand-700 underline">{t('Mes troupeaux')}</Link>{t(', ou utilisez le')} <Link to="/formulation?onglet=calcul" className="font-semibold text-brand-700 underline">{t('calcul détaillé')}</Link>.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" role="radiogroup" aria-label={t('Lot à nourrir')}>
            {lots.map((g) => {
              const on = g.id === groupId
              return (
                <button key={g.id} type="button" role="radio" aria-checked={on} onClick={() => { setGroupId(g.id); setObjective(memory.objectives[g.id] ?? '') }}
                  className={clsx(tile, on ? 'border-brand-700 bg-brand-50' : 'border-slate-200 bg-white hover:border-slate-300')}>
                  <span className="min-w-0 flex-1">
                    <span className="block font-semibold text-slate-900">{g.name}</span>
                    <span className="text-sm text-slate-500">{g.animals_count > 1 ? t('{{count}} animaux', { count: g.animals_count }) : t('1 animal')}</span>
                  </span>
                  {on && <Check className="size-5 text-brand-700" aria-hidden />}
                </button>
              )
            })}
          </div>
        )}
        <p className="mt-3 text-sm text-slate-500">{t('La catégorie, le stade et le poids moyen sont repris des fiches des animaux du lot.')}</p>
      </Card>

      <Card title={t('2. Objectif pour ce lot')}>
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t('Objectif')}>
          {[{ id: '', name: t('Non précisé') }, ...(objectives.data ?? pack?.objectives ?? []).map((o) => ({ id: String(o.id), name: t(o.name) }))].map((o) => (
            <button key={o.id} type="button" role="radio" aria-checked={objective === o.id} onClick={() => setObjective(o.id)}
              className={clsx('min-h-11 rounded-full border px-4 text-sm font-medium', objective === o.id ? 'border-brand-700 bg-brand-700 text-white' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50')}>
              {o.name}
            </button>
          ))}
        </div>
        <p className="mt-3 text-sm text-slate-500">{t("Les besoins dépendent de l'objectif : sans objectif, seules les références générales s'appliquent. Il est retenu pour ce lot sur cet appareil.")}</p>
      </Card>

      {groupId !== null && farmId !== null && (
        <MatchingTemplates farm={farmId} group={groupId} objective={objective ? Number(objective) : null} season={seasonId} isDemo={demoFarm} />
      )}

      {(seasons.data ?? []).length > 0 && (
        <div className="flex flex-wrap items-center gap-2" role="radiogroup" aria-label={t('Saison du calcul')}>
          <span className="text-sm font-medium text-slate-700">{t('Saison :')}</span>
          {(seasons.data ?? []).map((s) => (
            <button key={s.id} type="button" role="radio" aria-checked={s.id === seasonId} onClick={() => setSeasonChoice(s.id)}
              className={clsx('inline-flex min-h-10 items-center gap-1.5 rounded-full border px-3 text-sm font-medium',
                s.id === seasonId ? `${seasonTone(s)} border-transparent` : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50')}>
              <SeasonIcon season={s} className="size-4" /> {t(s.name)}
              {s.id === currentSeason.data?.season?.id && <span className="text-xs opacity-80">({t('en cours')})</span>}
            </button>
          ))}
        </div>
      )}

      <Card title={t('3. Vos aliments')}>
        {ingredients.isPending && fromPack.ingredients.length === 0 ? <Spinner /> : ready.length === 0 ? (
          <p className="text-sm text-slate-600">{t("Aucun aliment n'a encore de données validées par un expert : le calcul serait refusé.")}</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {ready.map((i) => {
              const on = picked.has(i.id)
              const price = priceOf.get(i.id)
              return (
                <button key={i.id} type="button" role="checkbox" aria-checked={on} aria-label={plainName(i.name)} onClick={() => toggle(i.id)}
                  className={clsx(tile, on ? 'border-brand-700 bg-brand-50' : 'border-slate-200 bg-white hover:border-slate-300')}>
                  <IngredientIcon category={i.category_code} />
                  <span className="min-w-0 flex-1">
                    <span className="block font-semibold text-slate-900">{plainName(i.name)}</span>
                    {i.local_names && <span className="block text-sm text-slate-600">{i.local_names}</span>}
                    <span className={clsx('text-sm', price ? 'text-slate-500' : 'text-mil-700')}>
                      {price ? `${formatMoney(price.price_per_kg_as_fed, price.currency)} / kg${price.seasonal ? ` · ${t('prix de saison')}` : ''}` : t('Prix inconnu')}
                    </span>
                    {levelOf.get(i.id) === 'SCARCE' && <span className="mt-1 inline-flex rounded-full bg-mil-100 px-2 py-0.5 text-xs font-semibold text-mil-700">{t('Rare en cette saison')}</span>}
                    {levelOf.get(i.id) === 'UNAVAILABLE' && <span className="mt-1 inline-flex rounded-full bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700">{t('Indisponible en cette saison')}</span>}
                  </span>
                  <span className={clsx('inline-flex size-6 shrink-0 items-center justify-center rounded border-2', on ? 'border-brand-700 bg-brand-700 text-white' : 'border-slate-300')}>
                    {on && <Check className="size-4" aria-hidden />}
                  </span>
                </button>
              )
            })}
          </div>
        )}
        {notReady > 0 && <p className="mt-3 text-sm text-slate-500">{t('{{count}} autre(s) aliment(s) sans données validées ne sont pas proposés.', { count: notReady })}</p>}
        {unpriced.length > 0 && (
          <p className="mt-3 text-sm font-medium text-mil-700">
            {unpriced.length > 1
              ? t('Sans prix connu, {{names}} seront exclus du calcul économique.', { names: unpriced.map((i) => plainName(i.name)).join(', ') })
              : t('Sans prix connu, {{names}} sera exclu du calcul économique.', { names: unpriced.map((i) => plainName(i.name)).join(', ') })}{' '}
            {t('Saisissez un prix dans le')} <Link to="/formulation?onglet=calcul" className="underline">{t('calcul détaillé')}</Link>.
          </p>
        )}
      </Card>


      <div className="sticky bottom-0 -mx-4 border-t border-slate-200 bg-white/95 px-4 py-3 pr-24 sm:static sm:mx-0 sm:flex sm:items-center sm:justify-between sm:gap-4 sm:border-0 sm:bg-transparent sm:p-0">
        <p className="mb-2 text-sm text-slate-500 sm:mb-0">{t('Ration au moindre coût. Le résultat sera une estimation, à faire vérifier par un expert.')}</p>
        <Button onClick={submit} loading={busy} icon={<Calculator className="size-4" />} className="w-full sm:w-auto">{t('Calculer la ration')}</Button>
      </div>
      <p className="text-sm text-slate-500">{t('Un seul animal, un prix ou un stock à préciser ? Utilisez le')} <Link to="/formulation?onglet=calcul" className="font-semibold text-brand-700 underline">{t('calcul détaillé')}</Link>.</p>
    </div>
  )
}
