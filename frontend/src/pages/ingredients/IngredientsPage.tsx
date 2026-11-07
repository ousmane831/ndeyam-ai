import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, Plus, Search, Upload, Wheat } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { ImportCsvModal } from '@/components/ImportCsvModal'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, EmptyState } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { PageHeader, td, th } from '@/components/ui/Layout'
import { Modal } from '@/components/ui/Modal'
import { Pagination } from '@/components/ui/Pagination'
import { Spinner } from '@/components/ui/Spinner'
import { ValidationBadge } from '@/features/reference/Workflow'
import { useFarm } from '@/hooks/useFarm'
import { useRoles } from '@/hooks/useRoles'
import { ingredientService, nutritionService, sourceService, compositionService, type IngredientFilters } from '@/services/nutrition'
import { applyServerErrors } from '@/utils/forms'
import { useForm } from 'react-hook-form'

const select = 'rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm'

interface NewIngredientValues {
  name: string
  category: string
  scope: string
  local_names: string
  description: string
  source: string
}

function NewIngredientModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { isReviewer } = useRoles()
  const { writableFarms, defaultWritableFarmId } = useFarm()
  const categories = useQuery({ queryKey: ['ingredient-categories'], queryFn: nutritionService.categories, staleTime: Infinity })
  const sources = useQuery({ queryKey: ['sources'], queryFn: () => sourceService.list(), enabled: isReviewer })
  const [serverError, setServerError] = useState<string | null>(null)
  const scopeOptions = [
    ...(isReviewer ? [{ value: 'catalog', label: 'Catalogue commun (géré par les experts)' }] : []),
    ...writableFarms.map((f) => ({ value: String(f.id), label: `Ingrédient privé — ${f.name}` })),
  ]
  const { register, handleSubmit, setError, reset, formState: { errors, isSubmitting } } = useForm<NewIngredientValues>({
    defaultValues: { name: '', category: '', scope: isReviewer ? 'catalog' : String(defaultWritableFarmId ?? ''), local_names: '', description: '', source: '' },
  })

  const onSubmit = handleSubmit(async (v) => {
    setServerError(null)
    if (!v.name.trim()) return setError('name', { message: 'Le nom est obligatoire.' })
    if (!v.category) return setError('category', { message: 'Choisissez une catégorie.' })
    try {
      const created = await ingredientService.create({
        name: v.name.trim(),
        category: Number(v.category),
        local_names: v.local_names,
        description: v.description,
        farm: v.scope === 'catalog' ? null : Number(v.scope),
        source: v.source ? Number(v.source) : null,
      })
      await queryClient.invalidateQueries({ queryKey: ['ingredients'] })
      reset()
      onClose()
      navigate(`/ingredients/${created.id}`)
    } catch (error) {
      setServerError(applyServerErrors(error, setError, ['name', 'category', 'local_names', 'description', 'source']))
    }
  })

  return (
    <Modal open={open} onClose={onClose} title="Nouvel ingrédient"
      footer={<><Button variant="secondary" onClick={onClose}>Annuler</Button><Button onClick={onSubmit} loading={isSubmitting}>Créer</Button></>}>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {serverError && <Alert tone="error">{serverError}</Alert>}
        <TextField label="Nom" required error={errors.name?.message} {...register('name')} />
        <SelectField label="Catégorie" required error={errors.category?.message}
          options={[{ value: '', label: 'Choisir…' }, ...(categories.data ?? []).map((c) => ({ value: String(c.id), label: c.name }))]} {...register('category')} />
        <SelectField label="Catalogue" options={scopeOptions} {...register('scope')}
          hint="Un ingrédient privé n'est visible que par votre exploitation ; ses valeurs doivent aussi être validées par un expert." />
        <TextField label="Noms locaux" {...register('local_names')} />
        <TextField label="Description" {...register('description')} />
        {isReviewer && (
          <SelectField label="Source documentaire" error={errors.source?.message}
            options={[{ value: '', label: 'Aucune pour le moment' }, ...(sources.data?.results ?? []).map((s) => ({ value: String(s.id), label: s.title }))]} {...register('source')} />
        )}
        <p className="text-xs text-slate-500">L'ingrédient est créé en brouillon. Ses compositions se saisissent ensuite dans sa fiche.</p>
      </form>
    </Modal>
  )
}

export function IngredientsPage() {
  const queryClient = useQueryClient()
  const { isReviewer } = useRoles()
  const { writableFarms } = useFarm()
  const [filters, setFilters] = useState<IngredientFilters>({ page: 1 })
  const [searchInput, setSearchInput] = useState('')
  const [creating, setCreating] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importSource, setImportSource] = useState('')
  const [importDemo, setImportDemo] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => setFilters((f) => ({ ...f, search: searchInput, page: 1 })), 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const ingredients = useQuery({ queryKey: ['ingredients', filters], queryFn: () => ingredientService.list(filters), placeholderData: keepPreviousData })
  const categories = useQuery({ queryKey: ['ingredient-categories'], queryFn: nutritionService.categories, staleTime: Infinity })
  const sources = useQuery({ queryKey: ['sources'], queryFn: () => sourceService.list(), enabled: isReviewer })
  const set = (key: keyof IngredientFilters, value: string) => setFilters((f) => ({ ...f, [key]: value, page: 1 }))

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ingrédients alimentaires"
        description="Catalogue commun validé par les experts et ingrédients propres à votre exploitation. Une valeur non renseignée est « inconnue », jamais zéro."
        actions={
          <>
            <Button variant="secondary" icon={<Download className="size-4" />}
              onClick={() => ingredientService.exportCsv(filters).catch((e: Error) => setExportError(e.message))}>
              Exporter
            </Button>
            {isReviewer && (
              <Button variant="secondary" icon={<Upload className="size-4" />} onClick={() => setImporting(true)}>
                Importer des compositions
              </Button>
            )}
            {(isReviewer || writableFarms.length > 0) && (
              <Button icon={<Plus className="size-4" />} onClick={() => setCreating(true)}>
                Nouvel ingrédient
              </Button>
            )}
          </>
        }
      />
      {exportError && <Alert tone="error">{exportError}</Alert>}

      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-4">
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
          <input type="search" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Nom, nom local…"
            aria-label="Rechercher un ingrédient" className="block w-full rounded-lg border border-slate-300 py-2.5 pr-3 pl-9 text-sm" />
        </div>
        <select aria-label="Catégorie" className={select} value={filters.category ?? ''} onChange={(e) => set('category', e.target.value)}>
          <option value="">Toutes catégories</option>
          {categories.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select aria-label="Catalogue" className={select} value={filters.scope ?? ''} onChange={(e) => set('scope', e.target.value)}>
          <option value="">Catalogue commun et privés</option>
          <option value="catalog">Catalogue commun</option>
          <option value="private">Ingrédients privés</option>
        </select>
        <select aria-label="Statut" className={select} value={filters.status ?? ''} onChange={(e) => set('status', e.target.value)}>
          <option value="">Tous statuts</option>
          <option value="VALIDATED">Validés</option>
          <option value="PENDING">En attente</option>
          <option value="DRAFT">Brouillons</option>
          <option value="REJECTED">Rejetés</option>
        </select>
      </div>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {ingredients.isPending ? (
          <div className="p-6"><Spinner /></div>
        ) : ingredients.isError ? (
          <div className="p-4"><Alert tone="error">{ingredients.error.message}</Alert></div>
        ) : ingredients.data.results.length === 0 ? (
          <EmptyState icon={<Wheat className="size-10" />} title="Aucun ingrédient">
            {isReviewer
              ? 'Ajoutez des ingrédients ou importez un fichier de compositions sourcées.'
              : "Le catalogue commun est alimenté par les experts. Vous pouvez créer un ingrédient privé pour votre exploitation."}
          </EmptyState>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-slate-200 bg-slate-50">
                  <tr><th className={th}>Ingrédient</th><th className={th}>Catégorie</th><th className={th}>Catalogue</th><th className={th}>Statut</th><th className={th}>Source</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {ingredients.data.results.map((i) => (
                    <tr key={i.id} className="hover:bg-slate-50/70">
                      <td className={td}>
                        <Link to={`/ingredients/${i.id}`} className="font-medium text-brand-700 hover:underline">{i.name}</Link>
                        {i.local_names && <p className="text-xs text-slate-500">{i.local_names}</p>}
                      </td>
                      <td className={td}>{i.category_name}</td>
                      <td className={td}>{i.scope === 'catalog' ? 'Commun' : <Badge>Privé</Badge>}</td>
                      <td className={td}><ValidationBadge status={i.status} isDemo={i.is_demo} /></td>
                      <td className={td}>{i.source?.title ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={filters.page ?? 1} pageSize={20} count={ingredients.data.count} onPageChange={(page) => setFilters((f) => ({ ...f, page }))} />
          </>
        )}
      </section>

      {creating && <NewIngredientModal open onClose={() => setCreating(false)} />}
      <ImportCsvModal
        open={importing}
        title="Importer des compositions"
        onClose={() => {
          setImporting(false)
          queryClient.invalidateQueries({ queryKey: ['ingredients'] })
        }}
        onImport={(file) => {
          if (!importSource) return Promise.reject(new Error('Choisissez la source documentaire du fichier.'))
          return compositionService.importCsv(file, Number(importSource), importDemo)
        }}
        help={
          <div className="space-y-3">
            <p>
              Colonnes : <code>ingredient, categorie, nutriment, systeme, valeur</code> (+ <code>date_reference, methode, origine</code>).
              Tout est importé en <strong>brouillon</strong> ; une valeur déjà validée n'est jamais modifiée ; une cellule vide reste inconnue.
            </p>
            <label className="block">
              <span className="mb-1 block font-medium text-slate-700">Source documentaire du fichier *</span>
              <select aria-label="Source de l'import" value={importSource} onChange={(e) => setImportSource(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2">
                <option value="">Choisir…</option>
                {sources.data?.results.map((s) => <option key={s.id} value={s.id}>{s.title}{s.is_demo ? ' (DEMO)' : ''}</option>)}
              </select>
            </label>
            <label className="inline-flex items-center gap-2">
              <input type="checkbox" className="accent-brand-600" checked={importDemo} onChange={(e) => setImportDemo(e.target.checked)} />
              Données de démonstration (DEMO)
            </label>
          </div>
        }
      />
    </div>
  )
}
