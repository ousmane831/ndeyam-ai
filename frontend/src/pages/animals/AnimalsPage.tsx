import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, PawPrint, Plus, Search, Upload } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { ImportCsvModal } from '@/components/ImportCsvModal'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, EmptyState } from '@/components/ui/Feedback'
import { PageHeader, td, th } from '@/components/ui/Layout'
import { Pagination } from '@/components/ui/Pagination'
import { Spinner } from '@/components/ui/Spinner'
import { useFarm } from '@/hooks/useFarm'
import { animalService, groupService, nomenclatureService, PAGE_SIZE, type AnimalFilters } from '@/services/animals'
import { formatAge, formatNumber } from '@/utils/format'

const STATUS_OPTIONS = [
  { value: '', label: 'Présents' },
  { value: 'SOLD', label: 'Vendus' },
  { value: 'DEAD', label: 'Morts' },
  { value: 'ARCHIVED', label: 'Archivés' },
]

const select = 'rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm'

export function AnimalsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { selectedFarmId, writableFarms, defaultWritableFarmId } = useFarm()
  const [filters, setFilters] = useState<AnimalFilters>({ page: 1 })
  const [searchInput, setSearchInput] = useState('')
  const [importOpen, setImportOpen] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => setFilters((f) => ({ ...f, search: searchInput, page: 1 })), 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const effective = { ...filters, farm: selectedFarmId }
  const animals = useQuery({
    queryKey: ['animals', effective],
    queryFn: () => animalService.list(effective),
    placeholderData: keepPreviousData,
  })
  const species = useQuery({ queryKey: ['species'], queryFn: nomenclatureService.species, staleTime: Infinity })
  const breeds = useQuery({ queryKey: ['breeds'], queryFn: () => nomenclatureService.breeds(), staleTime: Infinity })
  const groups = useQuery({ queryKey: ['groups', selectedFarmId], queryFn: () => groupService.list(selectedFarmId) })

  const setFilter = (key: keyof AnimalFilters, value: string) => setFilters((f) => ({ ...f, [key]: value, page: 1 }))
  const hasFilters = Boolean(filters.search || filters.species || filters.breed || filters.sex || filters.group || filters.status)
  const canCreate = writableFarms.length > 0

  const exportCsv = async () => {
    setExportError(null)
    try {
      await animalService.exportCsv(effective)
    } catch (e) {
      setExportError(e instanceof Error ? e.message : 'Export impossible.')
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mes animaux"
        description="Suivi individuel des animaux de vos exploitations."
        actions={
          <>
            <Button variant="secondary" icon={<Download className="size-4" />} onClick={exportCsv}>
              Exporter
            </Button>
            {canCreate && (
              <>
                <Button variant="secondary" icon={<Upload className="size-4" />} onClick={() => setImportOpen(true)}>
                  Importer
                </Button>
                <Button icon={<Plus className="size-4" />} onClick={() => navigate('/animaux/nouveau')}>
                  Ajouter un animal
                </Button>
              </>
            )}
          </>
        }
      />
      {exportError && <Alert tone="error">{exportError}</Alert>}

      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-6">
        <div className="relative sm:col-span-2">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Numéro, nom, observation…"
            aria-label="Rechercher un animal"
            className="block w-full rounded-lg border border-slate-300 py-2.5 pr-3 pl-9 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
          />
        </div>
        <select aria-label="Espèce" className={select} value={filters.species ?? ''} onChange={(e) => setFilter('species', e.target.value)}>
          <option value="">Toutes espèces</option>
          {species.data?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <select aria-label="Race" className={select} value={filters.breed ?? ''} onChange={(e) => setFilter('breed', e.target.value)}>
          <option value="">Toutes races</option>
          {breeds.data?.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        <select aria-label="Sexe" className={select} value={filters.sex ?? ''} onChange={(e) => setFilter('sex', e.target.value)}>
          <option value="">Mâles et femelles</option>
          <option value="M">Mâles</option>
          <option value="F">Femelles</option>
        </select>
        <select aria-label="Lot" className={select} value={filters.group ?? ''} onChange={(e) => setFilter('group', e.target.value)}>
          <option value="">Tous les lots</option>
          {groups.data?.results.map((g) => (
            <option key={g.id} value={g.id}>
              {g.name}
            </option>
          ))}
        </select>
        <select aria-label="Statut" className={`${select} lg:col-start-6`} value={filters.status ?? ''} onChange={(e) => setFilter('status', e.target.value)}>
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {animals.isPending ? (
          <div className="p-6">
            <Spinner />
          </div>
        ) : animals.isError ? (
          <div className="p-4">
            <Alert tone="error">{animals.error.message}</Alert>
          </div>
        ) : animals.data.results.length === 0 ? (
          <EmptyState
            icon={<PawPrint className="size-10" />}
            title={hasFilters ? 'Aucun animal ne correspond à ces critères' : 'Aucun animal enregistré'}
            action={
              !hasFilters && canCreate ? (
                <Button icon={<Plus className="size-4" />} onClick={() => navigate('/animaux/nouveau')}>
                  Ajouter mon premier animal
                </Button>
              ) : undefined
            }
          >
            {!hasFilters && canCreate && 'Ajoutez vos animaux un par un ou importez un fichier CSV.'}
          </EmptyState>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-slate-200 bg-slate-50">
                  <tr>
                    <th className={th}>Animal</th>
                    <th className={th}>Race</th>
                    <th className={th}>Sexe</th>
                    <th className={th}>Âge</th>
                    <th className={th}>Dernier poids</th>
                    <th className={th}>Lot</th>
                    <th className={th}>Statut</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {animals.data.results.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50/70">
                      <td className={td}>
                        <Link to={`/animaux/${a.id}`} className="font-medium text-brand-700 hover:underline">
                          {a.tag_number}
                        </Link>
                        {a.name && <span className="ml-2 text-slate-500">{a.name}</span>}
                        {a.is_demo && <span className="ml-2"><Badge tone="demo">DEMO</Badge></span>}
                      </td>
                      <td className={td}>{a.breed_name ?? '—'}</td>
                      <td className={td}>{a.sex_label}</td>
                      <td className={td}>{formatAge(a.age_days, a.birth_date_is_estimated)}</td>
                      <td className={td}>{a.last_weight ? `${formatNumber(a.last_weight.weight_kg)} kg` : '—'}</td>
                      <td className={td}>{a.group_name ?? '—'}</td>
                      <td className={td}>
                        <Badge tone={a.status === 'ACTIVE' ? 'brand' : 'neutral'}>{a.status_label}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={filters.page ?? 1}
              pageSize={PAGE_SIZE}
              count={animals.data.count}
              onPageChange={(page) => setFilters((f) => ({ ...f, page }))}
            />
          </>
        )}
      </section>

      <ImportCsvModal
        open={importOpen}
        title="Importer des animaux"
        onClose={() => {
          setImportOpen(false)
          queryClient.invalidateQueries({ queryKey: ['animals'] })
          queryClient.invalidateQueries({ queryKey: ['groups'] })
        }}
        onImport={(file) => animalService.importCsv(defaultWritableFarmId!, file)}
        help={
          <>
            <p>
              Fichier CSV (séparateur « ; » ou « , »). Colonnes obligatoires : <code>numero</code>, <code>sexe</code>. Facultatives :{' '}
              <code>espece, nom, race, date_naissance, age_estime_mois, poids_initial_kg, categorie, stade, lot, observations</code>.
            </p>
            <p className="mt-2">
              Exploitation de destination : <strong>{writableFarms.find((f) => f.id === defaultWritableFarmId)?.name}</strong>. Les numéros
              déjà présents ne sont jamais écrasés.
            </p>
          </>
        }
      />
    </div>
  )
}
