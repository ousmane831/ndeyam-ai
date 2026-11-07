import { api, type Paginated } from './api'

export type ProvenanceType = 'database' | 'engine' | 'document' | 'llm'

export interface Provenance {
  type: ProvenanceType
  label: string
  document_id?: number
  pages?: string
  formula_id?: number
}

export interface AssistantMessage {
  id: number
  role: 'USER' | 'ASSISTANT' | 'TOOL' | 'SYSTEM'
  content: string
  provenance: Provenance[]
  tool_calls: { name: string; input: Record<string, unknown>; ok: boolean }[]
  provider: string
  model: string
  error_code: string
  latency_ms: number | null
  created_at: string
}

export interface Conversation {
  id: number
  title: string
  farm: number | null
  is_archived: boolean
  messages_count: number
  created_at: string
  updated_at: string
}

export interface ConversationDetail extends Conversation {
  messages: AssistantMessage[]
}

export interface AssistantStatus {
  configured: boolean
  provider: string | null
  model: string | null
  message: string
}

const BASE = '/assistant/conversations/'

export const assistantService = {
  status: async () => (await api.get<AssistantStatus>(`${BASE}status/`)).data,
  list: async () => (await api.get<Paginated<Conversation>>(BASE, { params: { page_size: 50 } })).data,
  get: async (id: number) => (await api.get<ConversationDetail>(`${BASE}${id}/`)).data,
  create: async (farm: number | null) => (await api.post<Conversation>(BASE, { farm })).data,
  remove: async (id: number) => {
    await api.delete(`${BASE}${id}/`)
  },
  ask: async (id: number, content: string) =>
    (await api.post<AssistantMessage[]>(`${BASE}${id}/messages/`, { content }, { timeout: 180_000 })).data,
}
