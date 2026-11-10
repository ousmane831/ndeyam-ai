import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, ChevronUp, Download, FileText, RefreshCw, Search, Trash2, Upload } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, Card, EmptyState } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { PageHeader } from '@/components/ui/Layout'
import { ConfirmDialog, Modal } from '@/components/ui/Modal'
import { Pagination } from '@/components/ui/Pagination'
import { Spinner } from '@/components/ui/Spinner'
import { ValidationBadge, WorkflowActions } from '@/features/reference/Workflow'
import { useRoles } from '@/hooks/useRoles'
import { ApiError } from '@/services/api'
import { documentService, type TechnicalDocument } from '@/services/documents'
import { sourceService } from '@/services/nutrition'
import { formatDate, formatNumber } from '@/utils/format'
import { t as tr } from '@/i18n'
import { useTranslation } from 'react-i18next'

const errorText = (e: unknown) => (e instanceof ApiError ? Object.values(e.fieldErrors).flat().join(' ') || e.message : e instanceof Error ? e.message : tr('Action impossible.'))

function UploadModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const sources = useQuery({ queryKey: ['sources'], queryFn: () => sourceService.list() })
  const [file, setFile] = useState<File | null>(null)
  const [f, setF] = useState({ title: '', description: '', source: '', reference_date: '', is_demo: false })
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TechnicalDocument | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (k: 'title' | 'description' | 'source' | 'reference_date') => (e: { target: { value: string } }) => setF((s) => ({ ...s, [k]: e.target.value }))

  const submit = async () => {
    setError(null)
    if (!file) return setError(t('Choisissez un fichier PDF.'))
    if (!f.title.trim()) return setError(t('Le titre est obligatoire.'))
    setBusy(true)
    try {
      const doc = await documentService.upload({ ...f, title: f.title.trim(), file })
      setResult(doc)
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open title={t('Importer un document technique')} onClose={onClose}
      footer={result ? <Button onClick={onClose}>{t('Fermer')}</Button> : <><Button variant="secondary" onClick={onClose}>{t('Annuler')}</Button><Button onClick={submit} loading={busy} icon={<Upload className="size-4" />}>{t('Importer')}</Button></>}>
      {result ? (
        <div className="space-y-3">
          <Alert tone={result.processing_status === 'INDEXED' ? 'success' : 'error'} title={t(result.processing_status_label)}>
            {result.processing_status === 'INDEXED' ? t('{{pages}} page(s), {{chunks}} passage(s) indexé(s).', { pages: result.page_count, chunks: result.chunks_count }) : result.processing_error}
          </Alert>
          {result.warnings?.map((w) => <Alert key={w} tone="info">{w}</Alert>)}
          <p className="text-sm text-slate-500">{t("Le document est en brouillon : validez-le pour qu'il soit utilisé dans les recherches et par l'assistant.")}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {error && <Alert tone="error">{error}</Alert>}
          <input type="file" accept="application/pdf,.pdf" aria-label={t('Fichier PDF')} onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:font-medium file:text-brand-700" />
          <TextField label={t('Titre')} required value={f.title} onChange={set('title')} />
          <TextField label={t('Description')} value={f.description} onChange={set('description')} />
          <div className="grid gap-3 sm:grid-cols-2">
            <SelectField label={t('Source documentaire')} value={f.source} onChange={set('source')}
              options={[{ value: '', label: t('À renseigner avant validation') }, ...(sources.data?.results ?? []).map((s) => ({ value: String(s.id), label: s.title }))]} />
            <TextField label={t('Date de référence')} type="date" value={f.reference_date} onChange={set('reference_date')} />
          </div>
          <label className="inline-flex items-center gap-2 text-sm"><input type="checkbox" className="accent-brand-600" checked={f.is_demo} onChange={(e) => setF({ ...f, is_demo: e.target.checked })} /> {t('Document de démonstration (DEMO)')}</label>
          <p className="text-xs text-slate-500">{t("PDF de 20 Mo maximum, avec du texte sélectionnable : les documents scannés (images) ne sont pas lus, faute d'OCR.")}</p>
        </div>
      )}
    </Modal>
  )
}

function DocumentRow({ doc }: { doc: TechnicalDocument }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { isReviewer } = useRoles()
  const [open, setOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const chunks = useQuery({ queryKey: ['document-chunks', doc.id], queryFn: () => documentService.chunks(doc.id), enabled: open })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['documents'] })
  const reindex = useMutation({ mutationFn: () => documentService.reindex(doc.id), onSuccess: (d) => { setMessage(d.warnings?.join(' ') || t('Document réindexé.')); refresh() }, onError: (e) => setMessage(errorText(e)) })
  const removal = useMutation({ mutationFn: () => documentService.remove(doc.id), onSuccess: refresh })

  return (
    <li className="space-y-3 py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-slate-800">{doc.title}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <ValidationBadge status={doc.status} isDemo={doc.is_demo} />
            <Badge tone={doc.processing_status === 'INDEXED' ? 'brand' : doc.processing_status === 'FAILED' ? 'danger' : 'neutral'}>{t(doc.processing_status_label)}</Badge>
            {doc.page_count !== null && <span>{t('{{count}} p.', { count: doc.page_count })}</span>}
            <span>{t('{{count}} passage(s)', { count: doc.chunks_count })}</span>
            <span>{doc.embedded_chunks ? t('{{count}} vectorisé(s)', { count: doc.embedded_chunks }) : t('plein texte')}</span>
            <span>{doc.source?.title ?? t('sans source')}</span>
            {doc.reference_date && <span>{formatDate(doc.reference_date)}</span>}
          </div>
          {doc.processing_error && <p className="mt-1 text-sm text-red-700">{doc.processing_error}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="ghost" icon={<Download className="size-4" />} onClick={() => documentService.download(doc).catch((e) => setMessage(errorText(e)))}>PDF</Button>
          <Button size="sm" variant="ghost" icon={open ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />} onClick={() => setOpen((v) => !v)}>{t('Passages')}</Button>
          {isReviewer && <Button size="sm" variant="secondary" icon={<RefreshCw className="size-4" />} loading={reindex.isPending} onClick={() => reindex.mutate()}>{t('Réindexer')}</Button>}
          {isReviewer && <button type="button" onClick={() => setDeleting(true)} className="rounded-md p-2.5 text-slate-500 hover:text-red-600" aria-label={t('Supprimer {{title}}', { title: doc.title })}><Trash2 className="size-4" /></button>}
        </div>
      </div>
      {isReviewer && <WorkflowActions status={doc.status} canSubmit isReviewer onAction={(a, c) => documentService.act(doc.id, a, c).then(refresh)} />}
      {message && <Alert tone="info">{message}</Alert>}
      {open && (
        <div className="rounded-lg bg-slate-50 p-3">
          {chunks.isPending ? <Spinner /> : chunks.isError ? <Alert tone="error">{chunks.error.message}</Alert> : chunks.data.length === 0 ? <p className="text-sm text-slate-500">{t('Aucun passage.')}</p> : (
            <ol className="max-h-80 space-y-3 overflow-y-auto text-sm">
              {chunks.data.map((c) => (
                <li key={c.id}>
                  <p className="text-xs font-medium text-slate-500">{t('Passage {{index}} · p. {{pages}} · {{chars}} caractères', { index: c.chunk_index + 1, pages: `${c.page_start}${c.page_end !== c.page_start ? `-${c.page_end}` : ''}`, chars: formatNumber(c.char_count, 0) })}</p>
                  <p className="whitespace-pre-line text-slate-700">{c.text}</p>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
      <ConfirmDialog open={deleting} title={t('Supprimer ce document ?')} danger confirmLabel={t('Supprimer')} loading={removal.isPending}
        message={t('Le fichier et ses passages indexés seront supprimés.')} onConfirm={() => removal.mutate()} onCancel={() => setDeleting(false)} />
    </li>
  )
}

export function DocumentsPage() {
  const { t } = useTranslation()
  const { isReviewer } = useRoles()
  const [uploading, setUploading] = useState(false)
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [submitted, setSubmitted] = useState('')
  const [includeDrafts, setIncludeDrafts] = useState(false)
  const status = useQuery({ queryKey: ['documents-status'], queryFn: documentService.status, staleTime: 60_000 })
  const documents = useQuery({ queryKey: ['documents', page], queryFn: () => documentService.list({ page }), placeholderData: keepPreviousData })
  const results = useQuery({ queryKey: ['document-search', submitted, includeDrafts], queryFn: () => documentService.search(submitted, includeDrafts), enabled: submitted.length > 0 })

  return (
    <div className="space-y-6">
      <PageHeader title={t('Base documentaire')}
        description={t("Documents techniques validés, consultés par la recherche et par l'assistant NDEYAM AI. Chaque réponse cite le document et la page.")}
        actions={isReviewer && <Button icon={<Upload className="size-4" />} onClick={() => setUploading(true)}>{t('Importer un PDF')}</Button>} />

      {status.data && (
        <Alert tone={status.data.embeddings_configured ? 'success' : 'info'} title={status.data.embeddings_configured ? t('Recherche sémantique disponible') : t('Recherche plein texte')}>
          {status.data.embeddings_configured ? t('Modèle : {{model}} (stockage {{store}}).', { model: status.data.embedding_model, store: status.data.vector_store }) : status.data.message}
        </Alert>
      )}

      <Card title={t('Rechercher')}>
        <form onSubmit={(e) => { e.preventDefault(); setSubmitted(query.trim()) }} className="space-y-3">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-500" />
              <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('ex. conservation du tourteau, matière sèche du foin…')}
                aria-label={t('Recherche documentaire')} className="block w-full rounded-lg border border-slate-300 py-2.5 pr-3 pl-9 text-sm" />
            </div>
            <Button type="submit">{t('Rechercher')}</Button>
          </div>
          {isReviewer && (
            <label className="inline-flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" className="accent-brand-600" checked={includeDrafts} onChange={(e) => setIncludeDrafts(e.target.checked)} />
              {t('Inclure les documents non validés (aperçu expert)')}
            </label>
          )}
        </form>
        {submitted && (
          <div className="mt-5">
            {results.isPending ? <Spinner /> : results.isError ? <Alert tone="error">{results.error.message}</Alert> : (
              <div className="space-y-3">
                {results.data.warnings.map((w) => <Alert key={w} tone="info">{w}</Alert>)}
                {results.data.results.map((hit) => (
                  <article key={hit.chunk_id} className="rounded-lg border border-slate-200 p-4">
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                      <span className="font-medium text-slate-800">{hit.citation}</span>
                      <Badge>{hit.method === 'semantique' ? t('Sémantique') : t('Plein texte')}</Badge>
                      {hit.document_status !== 'VALIDATED' && <Badge tone="warning">{t('Non validé')}</Badge>}
                      {hit.is_demo && <Badge tone="demo">DEMO</Badge>}
                    </div>
                    <p className="mt-2 text-sm whitespace-pre-line text-slate-700">{hit.excerpt}</p>
                  </article>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>

      <Card title={t('Documents')}>
        {documents.isPending ? <Spinner /> : documents.isError ? <Alert tone="error">{documents.error.message}</Alert> : documents.data.results.length === 0 ? (
          <EmptyState icon={<FileText className="size-10" />} title={t('Aucun document disponible')}>
            {isReviewer ? t('Importez des guides techniques, fiches ou rapports en PDF, puis validez-les.') : t('Les experts n’ont pas encore publié de document validé.')}
          </EmptyState>
        ) : (
          <>
            <ul className="divide-y divide-slate-100">{documents.data.results.map((d) => <DocumentRow key={d.id} doc={d} />)}</ul>
            <div className="-mx-5 -mb-5 mt-4"><Pagination page={page} pageSize={20} count={documents.data.count} onPageChange={setPage} /></div>
          </>
        )}
      </Card>
      {uploading && <UploadModal onClose={() => setUploading(false)} />}
    </div>
  )
}
