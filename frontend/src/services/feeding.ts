import { api, type Paginated } from './api'
import { cleanParams, downloadFile } from './download'

export interface RationSummary {
  id: number
  farm: number
  name: string
  formula: number
  formula_name: string
  formula_status: string
  formula_status_label: string
  animal: number | null
  group: number | null
  target_label: string
  start_date: string
  end_date: string | null
  status: 'ACTIVE' | 'ENDED'
  status_label: string
  planned_as_fed_kg_per_animal_day: string | null
  is_demo: boolean
  notes: string
}

export interface FeedingRecordSummary {
  id: number
  farm: number
  ration: number | null
  fed_on: string
  ration_name: string | null
  animal: number | null
  group: number | null
  target_label: string
  number_of_animals: number | null
  quantity_calculated_kg: string | null
  quantity_distributed_kg: string
  quantity_consumed_kg: string | null
  quantity_refused_kg: string | null
  estimated_cost: string | null
  currency: string
  notes: string
  recorded_by_email: string | null
}

export interface FeedingSummary {
  records: number
  distributed_kg: string | null
  calculated_kg: string | null
  consumed_kg: string | null
  estimated_cost: string | null
  records_with_measured_consumption: number
  records_without_cost: number
  note: string
}

export interface RecordFilters {
  animal?: number
  group?: number
  ration?: string
  farm?: number | null
  page?: number
  fed_on__gte?: string
  fed_on__lte?: string
}

export const feedingService = {
  rations: async (params: { animal?: number; group?: number; farm?: number | null; status?: string }) =>
    (await api.get<Paginated<RationSummary>>('/rations/', { params: cleanParams({ ...params, page_size: 100 }) })).data,
  createRation: async (payload: Record<string, unknown>) => (await api.post<RationSummary>('/rations/', payload)).data,
  endRation: async (id: number, end_date: string) => (await api.post<RationSummary>(`/rations/${id}/end/`, { end_date })).data,
  removeRation: async (id: number) => {
    await api.delete(`/rations/${id}/`)
  },
  records: async (params: RecordFilters) =>
    (await api.get<Paginated<FeedingRecordSummary>>('/feeding-records/', { params: cleanParams(params) })).data,
  createRecord: async (payload: Record<string, unknown>) => (await api.post<FeedingRecordSummary>('/feeding-records/', payload)).data,
  removeRecord: async (id: number) => {
    await api.delete(`/feeding-records/${id}/`)
  },
  summary: async (params: RecordFilters) =>
    (await api.get<FeedingSummary>('/feeding-records/summary/', { params: cleanParams({ ...params, page: undefined }) })).data,
  exportCsv: (params: RecordFilters) =>
    downloadFile('/feeding-records/export/', cleanParams({ ...params, page: undefined }), 'historique_alimentaire.csv'),
}
