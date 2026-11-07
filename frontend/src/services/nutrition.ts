import type { ImportBatch } from '@/types/animal'
import type {
  Composition,
  InclusionConstraint,
  Ingredient,
  IngredientCategory,
  IngredientDetail,
  IngredientPrice,
  Nutrient,
  NutritionalReference,
  NutritionSystem,
  Requirement,
  SourceDocument,
  WorkflowAction,
} from '@/types/nutrition'
import { api, type Paginated } from './api'
import { cleanParams, downloadFile } from './download'

export interface IngredientFilters {
  page?: number
  search?: string
  category?: string
  status?: string
  scope?: string
  farm?: number | null
}

const workflow = (base: string) => (id: number, action: WorkflowAction, comment = '') =>
  api.post(`${base}${id}/${action}/`, { comment }).then((r) => r.data)

export const nutritionService = {
  nutrients: async () => (await api.get<Nutrient[]>('/nutrients/')).data,
  systems: async () => (await api.get<NutritionSystem[]>('/nutrition-systems/')).data,
  categories: async () => (await api.get<IngredientCategory[]>('/ingredient-categories/')).data,
  objectives: async () => (await api.get<{ id: number; name: string }[]>('/production-objectives/')).data,
}

export const ingredientService = {
  list: async (filters: IngredientFilters) =>
    (await api.get<Paginated<Ingredient>>('/ingredients/', { params: cleanParams({ ...filters, page_size: 20 }) })).data,
  all: async () => (await api.get<Paginated<Ingredient>>('/ingredients/', { params: { page_size: 100, is_active: true } })).data.results,
  get: async (id: number) => (await api.get<IngredientDetail>(`/ingredients/${id}/`)).data,
  create: async (payload: Record<string, unknown>) => (await api.post<Ingredient>('/ingredients/', payload)).data,
  update: async (id: number, payload: Record<string, unknown>) => (await api.patch<Ingredient>(`/ingredients/${id}/`, payload)).data,
  remove: async (id: number) => {
    await api.delete(`/ingredients/${id}/`)
  },
  act: workflow('/ingredients/') as (id: number, action: WorkflowAction, comment?: string) => Promise<Ingredient>,
  exportCsv: (filters: IngredientFilters) => downloadFile('/ingredients/export/', cleanParams({ ...filters, page: undefined }), 'compositions.csv'),
}

export const compositionService = {
  create: async (payload: Record<string, unknown>) => (await api.post<Composition>('/compositions/', payload)).data,
  update: async (id: number, payload: Record<string, unknown>) => (await api.patch<Composition>(`/compositions/${id}/`, payload)).data,
  remove: async (id: number) => {
    await api.delete(`/compositions/${id}/`)
  },
  act: workflow('/compositions/') as (id: number, action: WorkflowAction, comment?: string) => Promise<Composition>,
  async importCsv(file: File, source: number, isDemo: boolean): Promise<ImportBatch> {
    const form = new FormData()
    form.append('file', file)
    form.append('source', String(source))
    form.append('is_demo', String(isDemo))
    return (await api.post<ImportBatch>('/compositions/import/', form, { headers: { 'Content-Type': 'multipart/form-data' } })).data
  },
}

export const priceService = {
  list: async (params: { farm?: number | null; ingredient?: number; latest?: boolean }) =>
    (await api.get<Paginated<IngredientPrice>>('/ingredient-prices/', {
      params: cleanParams({ farm: params.farm, ingredient: params.ingredient, latest: params.latest ? 'true' : undefined, page_size: 100 }),
    })).data.results,
  create: async (payload: Record<string, unknown>) => (await api.post<IngredientPrice>('/ingredient-prices/', payload)).data,
  remove: async (id: number) => {
    await api.delete(`/ingredient-prices/${id}/`)
  },
}

export const referenceService = {
  list: async (params: { page?: number; species?: string; system?: string; status?: string; search?: string; is_demo?: string }) =>
    (await api.get<Paginated<NutritionalReference>>('/nutritional-references/', { params: cleanParams({ ...params, page_size: 20 }) })).data,
  usable: async (species: number, demo: boolean) =>
    (await api.get<Paginated<NutritionalReference>>('/nutritional-references/', {
      params: { species, page_size: 100, ...(demo ? { is_demo: true } : { status: 'VALIDATED', is_demo: false }) },
    })).data.results,
  get: async (id: number) => (await api.get<NutritionalReference>(`/nutritional-references/${id}/`)).data,
  create: async (payload: Record<string, unknown>) => (await api.post<NutritionalReference>('/nutritional-references/', payload)).data,
  update: async (id: number, payload: Record<string, unknown>) =>
    (await api.patch<NutritionalReference>(`/nutritional-references/${id}/`, payload)).data,
  act: workflow('/nutritional-references/') as (id: number, action: WorkflowAction, comment?: string) => Promise<NutritionalReference>,
  addRequirement: async (payload: Record<string, unknown>) => (await api.post<Requirement>('/requirements/', payload)).data,
  removeRequirement: async (id: number) => {
    await api.delete(`/requirements/${id}/`)
  },
}

export const inclusionService = {
  list: async (species?: number) =>
    (await api.get<Paginated<InclusionConstraint>>('/inclusion-constraints/', { params: cleanParams({ species, page_size: 100 }) })).data.results,
  create: async (payload: Record<string, unknown>) => (await api.post<InclusionConstraint>('/inclusion-constraints/', payload)).data,
  remove: async (id: number) => {
    await api.delete(`/inclusion-constraints/${id}/`)
  },
  act: workflow('/inclusion-constraints/') as (id: number, action: WorkflowAction, comment?: string) => Promise<InclusionConstraint>,
}

export const sourceService = {
  list: async (params: { page?: number; search?: string } = {}) =>
    (await api.get<Paginated<SourceDocument>>('/sources/', { params: cleanParams({ ...params, page_size: 100 }) })).data,
  create: async (payload: Partial<SourceDocument>) => (await api.post<SourceDocument>('/sources/', payload)).data,
  remove: async (id: number) => {
    await api.delete(`/sources/${id}/`)
  },
}
