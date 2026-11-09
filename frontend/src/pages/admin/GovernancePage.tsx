import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, Card, EmptyState } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { PageHeader, Tabs, td, th } from '@/components/ui/Layout'
import { Pagination } from '@/components/ui/Pagination'
import { Spinner } from '@/components/ui/Spinner'
import { useRoles } from '@/hooks/useRoles'
import { ApiError } from '@/services/api'
import { governanceService } from '@/services/governance'
import { sourceService } from '@/services/nutrition'
import { formatDateTime } from '@/utils/format'

type TabId = 'sources' | 'validations' | 'imports' | 'journal'

const SOURCE_TYPES = [
  ['COMPOSITION_TABLE', 'Table de composition / référentiel'], ['BOOK', 'Ouvrage'], ['ARTICLE', 'Article scientifique'],
  ['REPORT', 'Rapport technique'], ['LAB_ANALYSIS', 'Analyse de laboratoire'], ['FIELD_SURVEY', 'Enquête / mesure de terrain'],
  ['EXPERT_OPINION', "Avis d'expert documenté"], ['WEBSITE', 'Site web / base en ligne'], ['OTHER', 'Autre'],
]

function SourcesTab() {
  const queryClient = useQueryClient()
  const sources = useQuery({ queryKey: ['sources'], queryFn: () => sourceService.list() })
  const [f, setF] = useState({ title: '', authors: '', publisher: '', year: '', source_type: 'COMPOSITION_TABLE', identifier: '', url: '', is_demo: false })
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF((s) => ({ ...s, [k]: e.target.value }))
  const removal = useMutation({ mutationFn: sourceService.remove, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sources'] }), onError: (e: Error) => setError(e.message) })

  const add = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!f.title.trim()) return setError('Le titre est obligatoire.')
    try {
      await sourceService.create({ ...f, title: f.title.trim(), year: f.year ? Number(f.year) : null })
      setF({ ...f, title: '', authors: '', identifier: '', url: '', year: '' })
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    } catch (err) {
      setError(err instanceof ApiError ? Object.values(err.fieldErrors).flat().join(' ') || err.message : 'Création impossible.')
    }
  }

  return (
    <div className="space-y-4">
      <Card title="Nouvelle source documentaire">
        <form onSubmit={add} noValidate className="space-y-3">
          {error && <Alert tone="error">{error}</Alert>}
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <TextField label="Titre" required value={f.title} onChange={set('title')} />
            <TextField label="Auteurs" value={f.authors} onChange={set('authors')} />
            <TextField label="Éditeur / organisme" value={f.publisher} onChange={set('publisher')} />
            <TextField label="Année" inputMode="numeric" value={f.year} onChange={set('year')} />
            <SelectField label="Type" value={f.source_type} onChange={set('source_type')} options={SOURCE_TYPES.map(([value, label]) => ({ value, label }))} />
            <TextField label="Identifiant (DOI, ISBN, n° d'analyse)" value={f.identifier} onChange={set('identifier')} />
            <TextField label="Lien" value={f.url} onChange={set('url')} />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <label className="inline-flex items-center gap-2 text-sm"><input type="checkbox" checked={f.is_demo} onChange={(e) => setF({ ...f, is_demo: e.target.checked })} className="accent-brand-600" /> Source fictive (DEMO) — ne pourra jamais justifier une validation</label>
            <Button type="submit" size="sm" icon={<Plus className="size-4" />}>Ajouter</Button>
          </div>
        </form>
      </Card>
      <Card title="Sources">
        {sources.isPending ? <Spinner /> : sources.isError ? <Alert tone="error">{sources.error.message}</Alert> : sources.data.results.length === 0 ? <EmptyState title="Aucune source" /> : (
          <ul className="divide-y divide-slate-100">
            {sources.data.results.map((s) => (
              <li key={s.id} className="flex items-start justify-between gap-3 py-3 first:pt-0">
                <div>
                  <p className="font-medium text-slate-800">{s.title} {s.year && `(${s.year})`} {s.is_demo && <Badge tone="demo">DEMO</Badge>}</p>
                  <p className="text-xs text-slate-500">{[s.source_type_label, s.authors, s.publisher, s.identifier].filter(Boolean).join(' · ')}</p>
                </div>
                <button type="button" onClick={() => removal.mutate(s.id)} className="rounded-md p-2.5 text-slate-500 hover:text-red-600" aria-label={`Supprimer ${s.title}`}><Trash2 className="size-4" /></button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

function PagedTable<T extends { id: number }>({ queryKey, fetch, columns }: {
  queryKey: string
  fetch: (page: number) => Promise<{ count: number; results: T[] }>
  columns: { label: string; render: (row: T) => React.ReactNode }[]
}) {
  const [page, setPage] = useState(1)
  const data = useQuery({ queryKey: [queryKey, page], queryFn: () => fetch(page), placeholderData: keepPreviousData })
  return (
    <section className="overflow-hidden rounded-md border border-slate-200 bg-white">
      {data.isPending ? <div className="p-6"><Spinner /></div> : data.isError ? <div className="p-4"><Alert tone="error">{data.error.message}</Alert></div> : data.data.results.length === 0 ? <EmptyState title="Aucun enregistrement" /> : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-slate-200 bg-slate-50"><tr>{columns.map((c) => <th key={c.label} className={th}>{c.label}</th>)}</tr></thead>
              <tbody className="divide-y divide-slate-100">{data.data.results.map((row) => <tr key={row.id}>{columns.map((c) => <td key={c.label} className={td}>{c.render(row)}</td>)}</tr>)}</tbody>
            </table>
          </div>
          <Pagination page={page} pageSize={20} count={data.data.count} onPageChange={setPage} />
        </>
      )}
    </section>
  )
}

export function GovernancePage() {
  const { isAdmin, isReviewer } = useRoles()
  const [params, setParams] = useSearchParams()
  const tabs = [
    ...(isReviewer ? [{ id: 'sources' as TabId, label: 'Sources documentaires' }, { id: 'validations' as TabId, label: 'Historique des validations' }] : []),
    { id: 'imports' as TabId, label: 'Importations' },
    ...(isAdmin ? [{ id: 'journal' as TabId, label: "Journal d'activité" }] : []),
  ]
  const requested = params.get('onglet') as TabId
  const tab = tabs.some((t) => t.id === requested) ? requested : tabs[0].id

  return (
    <div className="space-y-6">
      <PageHeader title="Traçabilité des données" description="Sources, décisions de validation, importations et journal d'activité : chaque donnée de référence est rattachée à sa source." />
      <Tabs<TabId> tabs={tabs} active={tab} onChange={(id) => setParams({ onglet: id })} />
      {tab === 'sources' && <SourcesTab />}
      {tab === 'validations' && (
        <PagedTable queryKey="validation-records" fetch={governanceService.validations} columns={[
          { label: 'Date', render: (r) => formatDateTime(r.created_at) },
          { label: 'Donnée', render: (r) => `${r.model} #${r.object_id}` },
          { label: 'Décision', render: (r) => <Badge>{r.action_label}</Badge> },
          { label: 'Statut', render: (r) => `${r.from_status || '—'} → ${r.to_status}` },
          { label: 'Auteur', render: (r) => r.actor_email ?? '—' },
          { label: 'Commentaire', render: (r) => r.comment || '—' },
        ]} />
      )}
      {tab === 'imports' && (
        <PagedTable queryKey="import-batches" fetch={governanceService.imports} columns={[
          { label: 'Date', render: (r) => formatDateTime(r.started_at) },
          { label: 'Type', render: (r) => r.kind },
          { label: 'Fichier', render: (r) => r.file_name },
          { label: 'Résultat', render: (r) => `${r.created_rows} créée(s), ${r.updated_rows} mise(s) à jour, ${r.error_rows} erreur(s) / ${r.total_rows}` },
          { label: 'Statut', render: (r) => <Badge tone={r.error_rows ? 'warning' : 'brand'}>{r.status_label}</Badge> },
          { label: 'Par', render: (r) => r.imported_by_email ?? '—' },
        ]} />
      )}
      {tab === 'journal' && (
        <PagedTable queryKey="activity-logs" fetch={(page) => governanceService.activity({ page })} columns={[
          { label: 'Date', render: (r) => formatDateTime(r.created_at) },
          { label: 'Action', render: (r) => <span>{r.action_label}<span className="block font-mono text-xs text-slate-500">{r.action}</span></span> },
          { label: 'Objet', render: (r) => r.object_repr || '—' },
          { label: 'Exploitation', render: (r) => r.farm_name ?? '—' },
          { label: 'Utilisateur', render: (r) => r.actor_email ?? '—' },
        ]} />
      )}
    </div>
  )
}
