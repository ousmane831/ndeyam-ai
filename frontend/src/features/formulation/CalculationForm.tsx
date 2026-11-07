import { useQuery } from '@tanstack/react-query'
import { Calculator } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, Card } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { td, th } from '@/components/ui/Layout'
import { Spinner } from '@/components/ui/Spinner'
import { useFarm } from '@/hooks/useFarm'
import { ApiError } from '@/services/api'
import { animalService, groupService, nomenclatureService } from '@/services/animals'
import { formulaService } from '@/services/formulas'
import { ingredientService, nutritionService, priceService, referenceService } from '@/services/nutrition'
import { formatMoney } from '@/utils/format'
import { buildCalculationPayload, type IngredientChoice } from './payload'

const MODES = [
  { value: 'ECONOMIC', label: 'Économique', help: 'Coût minimal en respectant les besoins et contraintes validés.' },
  { value: 'BALANCED', label: 'Équilibré', help: 'Au plus près des cibles fixées par les experts ; le coût est un critère secondaire.' },
] as const

export function CalculationForm() {
  const navigate = useNavigate()
  const { writableFarms, defaultWritableFarmId, farms } = useFarm()
  const [farmId, setFarmId] = useState<number | null>(defaultWritableFarmId)
  const farm = farms.find((f) => f.id === farmId)
  const [name, setName] = useState('')
  const [mode, setMode] = useState<'ECONOMIC' | 'BALANCED'>('ECONOMIC')
  const [target, setTarget] = useState<'animal' | 'group' | 'profile'>('profile')
  const [p, setP] = useState({ animal: '', group: '', species: '', category: '', stage: '', objective: '', weight: '', age: '', reference: '', animals: '', days: '' })
  const [choices, setChoices] = useState<Record<number, IngredientChoice>>({})
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
  const visible = (ingredients.data ?? []).filter((i) => i.farm === null || i.farm === farmId)
  const selectedCount = Object.values(choices).filter((c) => c.selected).length
  const needsHeadcount = Object.values(choices).some((c) => c.selected && c.available.trim())
  const set = (k: keyof typeof p) => (e: { target: { value: string } }) => setP((s) => ({ ...s, [k]: e.target.value }))
  const choose = (id: number, patch: Partial<IngredientChoice>) =>
    setChoices((c) => ({ ...c, [id]: { ...(c[id] ?? { selected: false, price: '', available: '' }), ...patch } }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (farmId === null) return setError('Choisissez une exploitation.')
    if (!name.trim()) return setError('Donnez un nom à cette formule.')
    if (target === 'animal' && !p.animal) return setError('Choisissez un animal.')
    if (target === 'group' && !p.group) return setError('Choisissez un lot.')
    if (selectedCount === 0) return setError('Sélectionnez au moins un ingrédient.')
    if (needsHeadcount && (!p.animals || !p.days)) return setError('Indiquez le nombre d’animaux et la durée pour tenir compte des quantités disponibles.')
    setBusy(true)
    try {
      const payload = buildCalculationPayload({ farm: farmId, name, mode, target, ...p, species: p.species || String(speciesId ?? ''), choices })
      const { formula } = await formulaService.calculate(payload)
      if (formula) navigate(`/formulation/${formula.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? Object.values(err.fieldErrors).flat().join(' ') || err.message : 'Calcul impossible.')
    } finally {
      setBusy(false)
    }
  }

  if (writableFarms.length === 0) return <Alert tone="info">Le calcul de formules est réservé aux propriétaires et gestionnaires d'exploitation.</Alert>
  const opts = (items: { id: number; name: string }[] | undefined, empty: string) => [{ value: '', label: empty }, ...(items ?? []).map((i) => ({ value: String(i.id), label: i.name }))]

  return (
    <form onSubmit={submit} noValidate className="space-y-6">
      {error && <Alert tone="error">{error}</Alert>}
      {farm?.is_demo && <Alert tone="warning" title="Exploitation de démonstration">Le calcul utilisera uniquement des données DEMO : ne pas utiliser pour nourrir des animaux.</Alert>}

      <Card title="1. Formule">
        <div className="grid gap-4 sm:grid-cols-2">
          {writableFarms.length > 1 && (
            <SelectField label="Exploitation" value={farmId ? String(farmId) : ''} onChange={(e) => { setFarmId(Number(e.target.value)); setChoices({}) }}
              options={writableFarms.map((f) => ({ value: String(f.id), label: f.name }))} />
          )}
          <TextField label="Nom de la formule" required value={name} onChange={(e) => setName(e.target.value)} placeholder="ex. Embouche Tabaski — lot A" />
        </div>
        <fieldset className="mt-4">
          <legend className="mb-2 text-sm font-medium text-slate-700">Mode de calcul</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            {MODES.map((m) => (
              <label key={m.value} className={`flex cursor-pointer gap-3 rounded-lg border p-3 ${mode === m.value ? 'border-brand-500 bg-brand-50' : 'border-slate-200'}`}>
                <input type="radio" name="mode" value={m.value} checked={mode === m.value} onChange={() => setMode(m.value)} className="mt-1 accent-brand-600" />
                <span><span className="block font-medium text-slate-800">{m.label}</span><span className="text-sm text-slate-500">{m.help}</span></span>
              </label>
            ))}
          </div>
        </fieldset>
      </Card>

      <Card title="2. Animaux concernés">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-4 text-sm">
            {([['profile', 'Profil type'], ['animal', 'Un animal'], ['group', 'Un lot']] as const).map(([v, l]) => (
              <label key={v} className="inline-flex items-center gap-2"><input type="radio" name="target" checked={target === v} onChange={() => setTarget(v)} className="accent-brand-600" />{l}</label>
            ))}
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {target === 'animal' && (
              <SelectField label="Animal" value={p.animal} onChange={set('animal')} hint="Espèce, race, catégorie, stade, poids et âge sont repris de sa fiche."
                options={opts(animals.data?.map((a) => ({ id: a.id, name: `${a.tag_number}${a.name ? ` — ${a.name}` : ''}` })), 'Choisir…')} />
            )}
            {target === 'group' && <SelectField label="Lot" value={p.group} onChange={set('group')} options={opts(groups.data?.results, 'Choisir…')} />}
            {target !== 'animal' && species.data && species.data.length > 1 && <SelectField label="Espèce" value={p.species} onChange={set('species')} options={opts(species.data, 'Choisir…')} />}
            <SelectField label="Catégorie" value={p.category} onChange={set('category')} options={opts(categories.data, target === 'animal' ? 'Celle de la fiche' : 'Non précisée')} />
            <SelectField label="Stade physiologique" value={p.stage} onChange={set('stage')} options={opts(stages.data, target === 'animal' ? 'Celui de la fiche' : 'Non précisé')} />
            <SelectField label="Objectif" value={p.objective} onChange={set('objective')} options={opts(objectives.data, 'Non précisé')} />
            <TextField label="Poids (kg)" inputMode="decimal" value={p.weight} onChange={set('weight')} placeholder={target === 'animal' ? 'Dernier poids de la fiche' : ''} />
            <TextField label="Âge (mois)" inputMode="decimal" value={p.age} onChange={set('age')} />
          </div>
          <SelectField label="Référence nutritionnelle" value={p.reference} onChange={set('reference')}
            hint={references.data?.length === 0 ? 'Aucune référence utilisable pour cette espèce : le calcul sera refusé tant qu’un expert n’en a pas validé une.' : 'Le choix automatique retient la référence validée la plus adaptée au profil.'}
            options={[{ value: '', label: 'Automatique' }, ...(references.data ?? []).map((r) => ({ value: String(r.id), label: `${r.name} (${r.system_code})` }))]} />
        </div>
      </Card>

      <Card title={`3. Ingrédients disponibles (${selectedCount} sélectionné(s))`}>
        {ingredients.isPending ? <Spinner /> : visible.length === 0 ? (
          <p className="text-sm text-slate-500">Aucun ingrédient disponible. Ajoutez-en depuis la page Ingrédients.</p>
        ) : (
          <div className="space-y-4">
            <p className="text-xs text-slate-500">
              Le prix par défaut est le dernier prix enregistré dans l'exploitation ; vous pouvez le remplacer pour ce calcul. Un ingrédient sans
              valeur validée pour un nutriment requis sera exclu (jamais compté à zéro).
            </p>
            <div className="-mx-5 overflow-x-auto">
              <table className="w-full">
                <thead className="border-y border-slate-200 bg-slate-50"><tr>
                  <th className={th}>Utiliser</th><th className={th}>Ingrédient</th><th className={th}>Dernier prix</th><th className={th}>Prix pour ce calcul</th><th className={th}>Stock (kg brut)</th>
                </tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {visible.map((i) => {
                    const c = choices[i.id]
                    const last = priceByIngredient.get(i.id)
                    return (
                      <tr key={i.id}>
                        <td className={td}><input type="checkbox" aria-label={`Utiliser ${i.name}`} checked={Boolean(c?.selected)} onChange={(e) => choose(i.id, { selected: e.target.checked })} className="size-4 accent-brand-600" /></td>
                        <td className={td}>
                          <span className="font-medium text-slate-800">{i.name}</span>
                          <span className="ml-2 inline-flex gap-1">{i.status !== 'VALIDATED' && <Badge tone="warning">Non validé</Badge>}{i.is_demo && <Badge tone="demo">DEMO</Badge>}</span>
                        </td>
                        <td className={td}>{last ? formatMoney(last.price_per_kg_as_fed, last.currency) : <span className="text-slate-400">Aucun</span>}</td>
                        <td className={td}><input aria-label={`Prix de ${i.name}`} inputMode="decimal" disabled={!c?.selected} value={c?.price ?? ''} onChange={(e) => choose(i.id, { price: e.target.value })} className="w-28 rounded-lg border border-slate-300 px-2 py-1.5 text-sm disabled:bg-slate-50" /></td>
                        <td className={td}><input aria-label={`Stock de ${i.name}`} inputMode="decimal" disabled={!c?.selected} value={c?.available ?? ''} onChange={(e) => choose(i.id, { available: e.target.value })} className="w-28 rounded-lg border border-slate-300 px-2 py-1.5 text-sm disabled:bg-slate-50" /></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {needsHeadcount && (
              <div className="grid gap-4 sm:grid-cols-2">
                <TextField label="Nombre d'animaux nourris" inputMode="numeric" value={p.animals} onChange={set('animals')} />
                <TextField label="Durée couverte par le stock (jours)" inputMode="numeric" value={p.days} onChange={set('days')} />
              </div>
            )}
          </div>
        )}
      </Card>

      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-slate-500">Le résultat sera une estimation mathématique, à faire vérifier par un expert avant usage.</p>
        <Button type="submit" loading={busy} icon={<Calculator className="size-4" />}>Calculer la formule</Button>
      </div>
    </form>
  )
}
