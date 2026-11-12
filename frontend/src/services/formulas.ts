import type { CalculationPayload, Formula, RationTemplate } from '@/types/formula'
import type { WorkflowAction } from '@/types/nutrition'
import { api, type Paginated } from './api'
import { cleanParams } from './download'

export const formulaService = {
  list: async (params: { farm?: number | null; page?: number; status?: string; mode?: string }) =>
    (await api.get<Paginated<Formula>>('/formulas/', { params: cleanParams({ ...params, page_size: 20 }) })).data,
  all: async (farm?: number | null) =>
    (await api.get<Paginated<Formula>>('/formulas/', { params: cleanParams({ farm, page_size: 100 }) })).data.results,
  get: async (id: number) => (await api.get<Formula>(`/formulas/${id}/`)).data,
  calculate: async (payload: CalculationPayload) =>
    (await api.post<{ formula: Formula | null; result: Formula['result_snapshot'] & { status: string } }>('/formulas/calculate/', payload)).data,
  createManual: async (payload: {
    farm: number
    name: string
    species: number
    animal?: number | null
    group?: number | null
    notes?: string
    manual_items: { ingredient: number; quantity_as_fed_kg: string }[]
  }) => (await api.post<Formula>('/formulas/', payload)).data,
  remove: async (id: number) => {
    await api.delete(`/formulas/${id}/`)
  },
  review: async (id: number, action: 'submit-review' | 'validate' | 'reject', comment = '') =>
    (await api.post<Formula>(`/formulas/${id}/${action}/`, { comment })).data,
  compare: async (ids: number[]) => (await api.get<{ formulas: Formula[]; note: string }>('/formulas/compare/', { params: { ids: ids.join(',') } })).data,
}

/** Rations types validées : application immédiate, création à partir d'une formule validée. */
export const templateService = {
  list: async () => (await api.get<Paginated<RationTemplate>>('/ration-templates/', { params: { page_size: 100 } })).data.results,
  matching: async (params: { farm: number; group?: number | null; animal?: number | null; objective?: number | null; season?: number | null }) =>
    (await api.get<RationTemplate[]>('/ration-templates/matching/', { params: cleanParams(params) })).data,
  apply: async (id: number, payload: { farm: number; group?: number | null; animal?: number | null; objective?: number | null; season?: number | null; name?: string }) =>
    (await api.post<Formula>(`/ration-templates/${id}/apply/`, payload)).data,
  fromFormula: async (payload: { formula: number; name: string; weight_min_kg: string; weight_max_kg: string; conditions?: string }) =>
    (await api.post<RationTemplate>('/ration-templates/from-formula/', payload)).data,
  transition: async (id: number, action: WorkflowAction, comment = '') =>
    (await api.post<RationTemplate>(`/ration-templates/${id}/${action}/`, { comment })).data,
}
