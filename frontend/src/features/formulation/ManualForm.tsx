import { useQuery } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, Card } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { useFarm } from '@/hooks/useFarm'
import { ApiError } from '@/services/api'
import { nomenclatureService } from '@/services/animals'
import { formulaService } from '@/services/formulas'
import { ingredientService } from '@/services/nutrition'

/** Enregistrer la ration réellement utilisée par l'éleveur (quantités brutes) pour en analyser les apports et le coût. */
export function ManualForm() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { writableFarms, defaultWritableFarmId } = useFarm()
  const [farmId, setFarmId] = useState<number | null>(defaultWritableFarmId)
  const [name, setName] = useState('')
  const [rows, setRows] = useState<{ ingredient: string; qty: string }[]>([{ ingredient: '', qty: '' }])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const species = useQuery({ queryKey: ['species'], queryFn: nomenclatureService.species, staleTime: Infinity })
  const ingredients = useQuery({ queryKey: ['ingredients-all'], queryFn: ingredientService.all })
  const visible = (ingredients.data ?? []).filter((i) => i.farm === null || i.farm === farmId)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const items = rows.filter((r) => r.ingredient || r.qty)
    if (!farmId || !name.trim()) return setError(t('Indiquez l’exploitation et le nom de la ration.'))
    if (items.length === 0) return setError(t('Ajoutez au moins un ingrédient.'))
    for (const r of items) {
      if (!r.ingredient || !(Number(r.qty.replace(',', '.')) > 0)) return setError(t('Chaque ligne doit avoir un ingrédient et une quantité positive.'))
    }
    if (new Set(items.map((r) => r.ingredient)).size !== items.length) return setError(t('Chaque ingrédient ne doit apparaître qu’une fois.'))
    const speciesId = species.data?.[0]?.id
    if (!speciesId) return setError(t('Aucune espèce disponible.'))
    setBusy(true)
    try {
      const formula = await formulaService.createManual({
        farm: farmId, name: name.trim(), species: speciesId,
        manual_items: items.map((r) => ({ ingredient: Number(r.ingredient), quantity_as_fed_kg: r.qty.replace(',', '.') })),
      })
      navigate(`/formulation/${formula.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? Object.values(err.fieldErrors).flat().join(' ') || err.message : t('Enregistrement impossible.'))
    } finally {
      setBusy(false)
    }
  }

  if (writableFarms.length === 0) return <Alert tone="info">{t("La saisie de rations est réservée aux propriétaires et gestionnaires d'exploitation.")}</Alert>
  return (
    <form onSubmit={submit} noValidate className="space-y-6">
      {error && <Alert tone="error">{error}</Alert>}
      <Card title={t('Ration saisie manuellement')}>
        <div className="space-y-4">
          <p className="text-sm text-slate-500">
            {t("Indiquez ce que vous distribuez par animal et par jour (en kg de produit brut). NDEYAM AI calcule la matière sèche, les apports et le coût à partir des seules données validées, et signale ce qui manque. Aucune optimisation n'est faite.")}
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {writableFarms.length > 1 && (
              <SelectField label={t('Exploitation')} value={farmId ? String(farmId) : ''} onChange={(e) => setFarmId(Number(e.target.value))}
                options={writableFarms.map((f) => ({ value: String(f.id), label: f.name }))} />
            )}
            <TextField label={t('Nom de la ration')} required value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-2">
            {rows.map((row, index) => (
              <div key={index} className="grid grid-cols-[1fr_140px_auto] items-end gap-2">
                <SelectField label={index === 0 ? t('Ingrédient') : ''} aria-label={t('Ingrédient {{number}}', { number: index + 1 })} value={row.ingredient}
                  onChange={(e) => setRows((r) => r.map((x, i) => (i === index ? { ...x, ingredient: e.target.value } : x)))}
                  options={[{ value: '', label: t('Choisir…') }, ...visible.map((i) => ({ value: String(i.id), label: i.name }))]} />
                <TextField label={index === 0 ? t('kg brut / animal / j') : ''} aria-label={t('Quantité {{number}}', { number: index + 1 })} inputMode="decimal" value={row.qty}
                  onChange={(e) => setRows((r) => r.map((x, i) => (i === index ? { ...x, qty: e.target.value } : x)))} />
                <button type="button" onClick={() => setRows((r) => (r.length > 1 ? r.filter((_, i) => i !== index) : r))}
                  className="mb-1 rounded p-2 text-slate-500 hover:bg-red-50 hover:text-red-600" aria-label={t('Retirer la ligne {{number}}', { number: index + 1 })}>
                  <Trash2 className="size-4" />
                </button>
              </div>
            ))}
            <Button size="sm" variant="ghost" icon={<Plus className="size-4" />} onClick={() => setRows((r) => [...r, { ingredient: '', qty: '' }])}>{t('Ajouter une ligne')}</Button>
          </div>
        </div>
      </Card>
      <div className="flex justify-end"><Button type="submit" loading={busy}>{t('Enregistrer et analyser')}</Button></div>
    </form>
  )
}
