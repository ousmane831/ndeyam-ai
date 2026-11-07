import type { ImportBatch } from '@/types/animal'
import { api, type Paginated } from './api'
import { cleanParams } from './download'

export interface ValidationRecord {
  id: number
  model: string
  object_id: number
  action: string
  action_label: string
  from_status: string
  to_status: string
  comment: string
  actor_email: string | null
  created_at: string
}

export interface ActivityEntry {
  id: number
  action: string
  action_label: string
  actor_email: string | null
  farm: number | null
  farm_name: string | null
  object_repr: string
  details: Record<string, unknown>
  created_at: string
}

export const governanceService = {
  validations: async (page = 1) =>
    (await api.get<Paginated<ValidationRecord>>('/validation-records/', { params: { page, page_size: 20 } })).data,
  imports: async (page = 1) =>
    (await api.get<Paginated<ImportBatch & { started_at: string; imported_by_email: string | null }>>('/import-batches/', {
      params: { page, page_size: 20 },
    })).data,
  activity: async (params: { page?: number; search?: string }) =>
    (await api.get<Paginated<ActivityEntry>>('/activity-logs/', { params: cleanParams({ ...params, page_size: 20 }) })).data,
}
