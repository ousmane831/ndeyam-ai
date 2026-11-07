import type { SourceRef, ValidationStatus, WorkflowAction } from '@/types/nutrition'
import { api, type Paginated } from './api'
import { cleanParams, downloadFile } from './download'

export interface TechnicalDocument {
  id: number
  title: string
  description: string
  language: string
  source: SourceRef | null
  reference_date: string | null
  is_demo: boolean
  size_bytes: number
  page_count: number | null
  processing_status: 'UPLOADED' | 'PROCESSING' | 'INDEXED' | 'FAILED'
  processing_status_label: string
  processing_error: string
  indexed_at: string | null
  embedding_model: string
  chunks_count: number
  embedded_chunks: number
  uploaded_by_email: string | null
  status: ValidationStatus
  status_label: string
  validated_by_email: string | null
  validated_at: string | null
  validation_comment: string
  created_at: string
  warnings?: string[]
}

export interface SearchHit {
  chunk_id: number
  document_id: number
  document_title: string
  pages: string
  source: string | null
  document_status: ValidationStatus
  is_demo: boolean
  excerpt: string
  score: number
  method: 'semantique' | 'plein_texte'
  citation: string
}

export interface SearchResponse {
  results: SearchHit[]
  method: 'semantique' | 'plein_texte' | null
  warnings: string[]
}

export interface DocumentChunk {
  id: number
  chunk_index: number
  page_start: number | null
  page_end: number | null
  char_count: number
  text: string
}

export const documentService = {
  list: async (params: { page?: number; status?: string; search?: string }) =>
    (await api.get<Paginated<TechnicalDocument>>('/documents/', { params: cleanParams({ ...params, page_size: 20 }) })).data,
  async upload(payload: { file: File; title: string; description: string; source: string; reference_date: string; is_demo: boolean }) {
    const form = new FormData()
    form.append('file', payload.file)
    form.append('title', payload.title)
    form.append('description', payload.description)
    if (payload.source) form.append('source', payload.source)
    if (payload.reference_date) form.append('reference_date', payload.reference_date)
    form.append('is_demo', String(payload.is_demo))
    return (await api.post<TechnicalDocument>('/documents/', form, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 180_000 })).data
  },
  update: async (id: number, payload: Record<string, unknown>) => (await api.patch<TechnicalDocument>(`/documents/${id}/`, payload)).data,
  remove: async (id: number) => {
    await api.delete(`/documents/${id}/`)
  },
  reindex: async (id: number) => (await api.post<TechnicalDocument>(`/documents/${id}/reindex/`, {}, { timeout: 180_000 })).data,
  act: async (id: number, action: WorkflowAction, comment = '') => (await api.post<TechnicalDocument>(`/documents/${id}/${action}/`, { comment })).data,
  chunks: async (id: number) => (await api.get<DocumentChunk[]>(`/documents/${id}/chunks/`)).data,
  download: (doc: TechnicalDocument) => downloadFile(`/documents/${doc.id}/file/`, {}, `${doc.title}.pdf`),
  search: async (q: string, includeUnvalidated = false) =>
    (await api.get<SearchResponse>('/documents/search/', { params: cleanParams({ q, include_unvalidated: includeUnvalidated || undefined }) })).data,
  status: async () =>
    (await api.get<{ embeddings_configured: boolean; embedding_provider: string | null; embedding_model: string | null; vector_store: string; message: string }>(
      '/documents/status/',
    )).data,
}
