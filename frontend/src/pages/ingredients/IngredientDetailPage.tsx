import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, Card } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { DefinitionList, PageHeader, td, th } from '@/components/ui/Layout'
import { ConfirmDialog } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { ValidationBadge, WorkflowActions } from '@/features/reference/Workflow'
import { useFarm } from '@/hooks/useFarm'
import { useRoles } from '@/hooks/useRoles'
import { ApiError } from '@/services/api'
import { compositionService, ingredientService, priceService, sourceService } from '@/services/nutrition'
import type { IngredientDetail } from '@/types/nutrition'
import { formatDate, formatMoney, formatNumber, todayIso } from '@/utils/format'

function errorText(e: unknown) {
  if (e instanceof ApiError) return Object.values(e.fieldErrors).flat().join(' ') || e.message
  return e instanceof Error ? e.message : 'Action impossible.'
}

function AddCompositionForm({ ingredient, onDone }: { ingredient: IngredientDetail; onDone: () => void }) {
  const { isReviewer } = useRoles()
  const sources = useQuery({ queryKey: ['sources'], queryFn: () => sourceService.list() })
  const [nutrient, setNutrient] = useState('')
  const [value, setValue] = useState('')
  const [source, setSource] = useState('')
  const [refDate, setRefDate] = useState('')
  const [method, setMethod] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const nutrients = ingredient.composition_table.map((r) => r.nutrient)
  const selected = nutrients.find((n) => String(n.id) === nutrient)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const n = Number(value.replace(',', '.'))
    if (!nutrient) return setError('Choisissez le nutriment.')
    if (value.trim() === '' || Number.isNaN(n) || n < 0) return setError('Valeur positive ou nulle attendue.')
    if (selected?.category === 'DRY_MATTER' && !(n > 0 && n <= 1000)) return setError('La matière sèche est comprise entre 0 et 1000 g/kg brut.')
    setBusy(true)
    try {
      await compositionService.create({
        ingredient: ingredient.id, nutrient: Number(nutrient), value: String(n), source: source ? Number(source) : null,
        reference_date: refDate || null, analysis_method: method, is_demo: ingredient.is_demo,
      })
      setValue('')
      onDone()
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-3 rounded-lg border border-dashed border-slate-300 p-4">
      <p className="text-sm font-medium text-slate-800">Ajouter une valeur</p>
      {error && <Alert tone="error">{error}</Alert>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <SelectField label="Nutriment" value={nutrient} onChange={(e) => setNutrient(e.target.value)}
          options={[{ value: '', label: 'Choisir…' }, ...nutrients.map((n) => ({ value: String(n.id), label: `${n.code}${n.system_code ? ` (${n.system_code})` : ''} — ${n.unit_label}` }))]} />
        <TextField label={`Valeur${selected ? ` (${selected.unit_label})` : ''}`} inputMode="decimal" value={value} onChange={(e) => setValue(e.target.value)} />
        <SelectField label="Source" value={source} onChange={(e) => setSource(e.target.value)}
          options={[{ value: '', label: 'Non renseignée' }, ...(sources.data?.results ?? []).map((s) => ({ value: String(s.id), label: s.title }))]} />
        <TextField label="Date de référence" type="date" value={refDate} onChange={(e) => setRefDate(e.target.value)} />
        <TextField label="Méthode d'analyse" value={method} onChange={(e) => setMethod(e.target.value)} />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-500">
          La valeur est enregistrée en brouillon{isReviewer ? '' : ' et doit être validée par un expert'}. Sans source, elle ne pourra pas être validée.
        </p>
        <Button type="submit" size="sm" loading={busy} icon={<Plus className="size-4" />}>Ajouter</Button>
      </div>
    </form>
  )
}

function PricesCard({ ingredient }: { ingredient: IngredientDetail }) {
  const queryClient = useQueryClient()
  const { writableFarms, defaultWritableFarmId, selectedFarmId, canWrite } = useFarm()
  const farmId = ingredient.farm ?? selectedFarmId ?? defaultWritableFarmId
  const key = ['prices', ingredient.id, farmId]
  const prices = useQuery({ queryKey: key, queryFn: () => priceService.list({ farm: farmId, ingredient: ingredient.id }), enabled: farmId !== null })
  const [price, setPrice] = useState('')
  const [date, setDate] = useState(todayIso())
  const [supplier, setSupplier] = useState('')
  const [stock, setStock] = useState('')
  const [error, setError] = useState<string | null>(null)
  const removal = useMutation({ mutationFn: priceService.remove, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['prices'] }) })
  const writable = farmId !== null && canWrite(farmId)

  const add = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const n = Number(price.replace(',', '.'))
    if (!(n > 0)) return setError('Prix positif attendu (par kg brut).')
    try {
      await priceService.create({ farm: farmId, ingredient: ingredient.id, price_per_kg_as_fed: String(n), valid_from: date, supplier,
        quantity_available_kg: stock ? stock.replace(',', '.') : null })
      setPrice('')
      setStock('')
      queryClient.invalidateQueries({ queryKey: ['prices'] })
    } catch (err) {
      setError(errorText(err))
    }
  }

  if (farmId === null) return writableFarms.length ? null : <Card title="Prix"><p className="text-sm text-slate-500">Choisissez une exploitation pour voir ses prix.</p></Card>
  return (
    <Card title="Prix dans votre exploitation">
      <div className="space-y-4">
        {prices.isPending ? <Spinner /> : prices.isError ? <Alert tone="error">{prices.error.message}</Alert> : prices.data.length === 0 ? (
          <p className="text-sm text-slate-500">Aucun prix enregistré : l'ingrédient ne pourra pas être utilisé en mode économique.</p>
        ) : (
          <div className="-mx-5 overflow-x-auto">
            <table className="w-full">
              <thead className="border-y border-slate-200 bg-slate-50"><tr><th className={th}>Date</th><th className={th}>Prix / kg brut</th><th className={th}>Fournisseur</th><th className={th}>Disponible</th>{writable && <th className={th} />}</tr></thead>
              <tbody className="divide-y divide-slate-100">
                {prices.data.map((p, i) => (
                  <tr key={p.id}>
                    <td className={td}>{formatDate(p.valid_from)} {i === 0 && <Badge tone="brand">Actuel</Badge>}</td>
                    <td className={`${td} font-medium`}>{formatMoney(p.price_per_kg_as_fed, p.currency)}</td>
                    <td className={td}>{p.supplier || '—'}</td>
                    <td className={td}>{p.quantity_available_kg ? `${formatNumber(p.quantity_available_kg)} kg` : '—'}</td>
                    {writable && (
                      <td className={`${td} text-right`}>
                        <button type="button" onClick={() => removal.mutate(p.id)} className="rounded-md p-2.5 text-slate-500 hover:bg-red-50 hover:text-red-600" aria-label="Supprimer le prix">
                          <Trash2 className="size-4" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {writable && (
          <form onSubmit={add} noValidate className="space-y-3">
            {error && <Alert tone="error">{error}</Alert>}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <TextField label="Prix par kg brut (FCFA)" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} />
              <TextField label="Date du prix" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
              <TextField label="Fournisseur / marché" value={supplier} onChange={(e) => setSupplier(e.target.value)} />
              <TextField label="Quantité disponible (kg brut)" inputMode="decimal" value={stock} onChange={(e) => setStock(e.target.value)} />
            </div>
            <div className="flex justify-end"><Button type="submit" size="sm" icon={<Plus className="size-4" />}>Enregistrer le prix</Button></div>
          </form>
        )}
      </div>
    </Card>
  )
}

export function IngredientDetailPage() {
  const { id } = useParams()
  const ingredientId = Number(id)
  const queryClient = useQueryClient()
  const { isReviewer } = useRoles()
  const { canWrite } = useFarm()
  const ingredient = useQuery({ queryKey: ['ingredient', ingredientId], queryFn: () => ingredientService.get(ingredientId) })
  const [toDelete, setToDelete] = useState<number | null>(null)
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['ingredient', ingredientId] })
  const removeComp = useMutation({ mutationFn: compositionService.remove, onSuccess: () => { setToDelete(null); refresh() } })

  if (ingredient.isPending) return <Spinner />
  if (ingredient.isError) return <Alert tone="error">{ingredient.error.message}</Alert>
  const ing = ingredient.data
  const writable = ing.farm === null ? isReviewer : canWrite(ing.farm)
  const known = ing.composition_table.filter((r) => r.validated_value !== null).length

  return (
    <div className="space-y-6">
      <Link to="/ingredients" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"><ArrowLeft className="size-4" /> Ingrédients</Link>
      <PageHeader
        title={ing.name}
        description={<span className="flex flex-wrap items-center gap-2">{ing.category_name} · {ing.scope === 'catalog' ? 'Catalogue commun' : 'Ingrédient privé'} <ValidationBadge status={ing.status} isDemo={ing.is_demo} /></span>}
        actions={<WorkflowActions status={ing.status} canSubmit={writable} isReviewer={isReviewer} onAction={(a, c) => ingredientService.act(ing.id, a, c).then(refresh)} />}
      />
      {ing.validation_comment && <Alert tone={ing.status === 'REJECTED' ? 'warning' : 'info'} title="Commentaire de validation">{ing.validation_comment}</Alert>}

      <Card>
        <DefinitionList items={[
          { label: 'Noms locaux', value: ing.local_names || '—' },
          { label: 'Source', value: ing.source?.title ?? 'Non renseignée' },
          { label: 'Validé par', value: ing.validated_by_email ? `${ing.validated_by_email} (${formatDate(ing.validated_at)})` : '—' },
          { label: 'Description', value: ing.description || '—' },
          { label: 'Observations', value: ing.observations || '—' },
        ]} />
      </Card>

      <Card title={`Composition nutritionnelle (${known} valeur(s) validée(s) sur ${ing.composition_table.length} nutriments)`}>
        <div className="space-y-5">
          <p className="text-xs text-slate-500">
            Valeurs par kg de matière sèche (MS), sauf la teneur en MS (g/kg de produit brut). Seules les valeurs validées et non DEMO sont
            utilisées dans les calculs.
          </p>
          <div className="-mx-5 overflow-x-auto">
            <table className="w-full">
              <thead className="border-y border-slate-200 bg-slate-50">
                <tr><th className={th}>Nutriment</th><th className={th}>Valeur utilisée</th><th className={th}>Valeurs enregistrées</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {ing.composition_table.map((row) => (
                  <tr key={row.nutrient.id} className="align-top">
                    <td className={td}>
                      <p className="font-medium text-slate-800">{row.nutrient.code}{row.nutrient.system_code && <span className="ml-1 text-xs text-slate-500">({row.nutrient.system_code})</span>}</p>
                      <p className="text-xs text-slate-500">{row.nutrient.name} · {row.nutrient.unit_label}</p>
                    </td>
                    <td className={td}>
                      {row.validated_value !== null ? (
                        <span className="font-semibold text-slate-900">{formatNumber(row.validated_value, 4)}</span>
                      ) : (
                        <span className="text-slate-500 italic">Inconnue</span>
                      )}
                    </td>
                    <td className={td}>
                      {row.values.length === 0 ? <span className="text-slate-500">—</span> : (
                        <ul className="space-y-3">
                          {row.values.map((c) => (
                            <li key={c.id} className="space-y-1.5">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="font-medium">{formatNumber(c.value, 4)}</span>
                                <ValidationBadge status={c.status} isDemo={c.is_demo} />
                                <span className="text-xs text-slate-500">{c.source?.title ?? 'sans source'}{c.reference_date ? ` · ${formatDate(c.reference_date)}` : ''}</span>
                                {writable && c.status !== 'VALIDATED' && (
                                  <button type="button" onClick={() => setToDelete(c.id)} className="rounded p-1 text-slate-500 hover:text-red-600" aria-label="Supprimer la valeur">
                                    <Trash2 className="size-3.5" />
                                  </button>
                                )}
                              </div>
                              <WorkflowActions status={c.status} canSubmit={writable} isReviewer={isReviewer}
                                onAction={(a, comment) => compositionService.act(c.id, a, comment).then(refresh)} />
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {writable && <AddCompositionForm ingredient={ing} onDone={refresh} />}
        </div>
      </Card>

      <PricesCard ingredient={ing} />

      <ConfirmDialog open={toDelete !== null} title="Supprimer cette valeur ?" message="La valeur non validée sera supprimée." confirmLabel="Supprimer" danger
        loading={removeComp.isPending} onConfirm={() => toDelete && removeComp.mutate(toDelete)} onCancel={() => setToDelete(null)} />
    </div>
  )
}
