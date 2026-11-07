import type {
  Animal,
  AnimalGroup,
  AnimalGrowth,
  AnimalPayload,
  GroupGrowth,
  HistoryEvent,
  ImportBatch,
  NamedRef,
  Observation,
  Species,
  Weighing,
  WeighingMethod,
} from '@/types/animal'
import { api, type Paginated } from './api'
import { cleanParams, downloadFile } from './download'

export interface AnimalFilters {
  farm?: number | null
  page?: number
  search?: string
  species?: string
  breed?: string
  sex?: string
  group?: string
  status?: string
  ordering?: string
}

export const PAGE_SIZE = 20

export const nomenclatureService = {
  species: async () => (await api.get<Species[]>('/species/')).data,
  breeds: async (species?: number) => (await api.get<NamedRef[]>('/breeds/', { params: cleanParams({ species }) })).data,
  categories: async (species?: number) =>
    (await api.get<NamedRef[]>('/animal-categories/', { params: cleanParams({ species }) })).data,
  stages: async (species?: number) =>
    (await api.get<NamedRef[]>('/physiological-stages/', { params: cleanParams({ species }) })).data,
}

export const animalService = {
  async list(filters: AnimalFilters): Promise<Paginated<Animal>> {
    return (await api.get<Paginated<Animal>>('/animals/', { params: cleanParams({ ...filters, page_size: PAGE_SIZE }) })).data
  },
  /** Animaux présents d'une exploitation pour les listes de choix (100 maximum). */
  options: async (farm: number | null) =>
    (await api.get<Paginated<Animal>>('/animals/', { params: cleanParams({ farm, page_size: 100, ordering: 'tag_number' }) })).data.results,
  get: async (id: number) => (await api.get<Animal>(`/animals/${id}/`)).data,
  create: async (payload: AnimalPayload) => (await api.post<Animal>('/animals/', payload)).data,
  update: async (id: number, payload: Partial<AnimalPayload>) => (await api.patch<Animal>(`/animals/${id}/`, payload)).data,
  remove: async (id: number) => {
    await api.delete(`/animals/${id}/`)
  },
  archive: async (id: number, status: 'SOLD' | 'DEAD' | 'ARCHIVED', note: string) =>
    (await api.post<Animal>(`/animals/${id}/archive/`, { status, note })).data,
  restore: async (id: number) => (await api.post<Animal>(`/animals/${id}/restore/`)).data,
  history: async (id: number) => (await api.get<HistoryEvent[]>(`/animals/${id}/history/`)).data,
  growth: async (id: number) => (await api.get<AnimalGrowth>(`/growth/animals/${id}/`)).data,
  observations: async (id: number) => (await api.get<Observation[]>(`/animals/${id}/observations/`)).data,
  addObservation: async (id: number, payload: { text: string; kind: string; observed_on?: string }) =>
    (await api.post<Observation>(`/animals/${id}/observations/`, payload)).data,
  removeObservation: async (id: number, observationId: number) => {
    await api.delete(`/animals/${id}/observations/${observationId}/`)
  },
  exportCsv: (filters: AnimalFilters) => downloadFile('/animals/export/', cleanParams({ ...filters, page: undefined }), 'animaux.csv'),
  async importCsv(farm: number, file: File): Promise<ImportBatch> {
    const form = new FormData()
    form.append('farm', String(farm))
    form.append('file', file)
    return (await api.post<ImportBatch>('/animals/import/', form, { headers: { 'Content-Type': 'multipart/form-data' } })).data
  },
}

export const groupService = {
  list: async (farm?: number | null) =>
    (await api.get<Paginated<AnimalGroup>>('/groups/', { params: cleanParams({ farm, page_size: 100 }) })).data,
  create: async (payload: { farm: number; name: string; species?: number | null; description?: string }) =>
    (await api.post<AnimalGroup>('/groups/', payload)).data,
  update: async (id: number, payload: Partial<AnimalGroup>) => (await api.patch<AnimalGroup>(`/groups/${id}/`, payload)).data,
  remove: async (id: number) => {
    await api.delete(`/groups/${id}/`)
  },
  growth: async (id: number) => (await api.get<GroupGrowth>(`/growth/groups/${id}/`)).data,
}

export const weighingService = {
  list: async (params: { animal?: number; farm?: number | null; page_size?: number }) =>
    (await api.get<Paginated<Weighing>>('/weighings/', { params: cleanParams(params) })).data,
  create: async (payload: { animal: number; weight_kg: string; weighed_on: string; method: WeighingMethod; observations?: string }) =>
    (await api.post<Weighing>('/weighings/', payload)).data,
  remove: async (id: number) => {
    await api.delete(`/weighings/${id}/`)
  },
  bulk: async (payload: {
    weighed_on: string
    method: WeighingMethod
    entries: { animal: number; weight_kg: string; observations?: string }[]
  }) => (await api.post<Weighing[]>('/weighings/bulk/', payload)).data,
}
