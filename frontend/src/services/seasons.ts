import type { AvailabilityLevel, CurrentSeason, IngredientAvailability, Season, SeasonalAdvice } from '@/types/season'
import type { WorkflowAction } from '@/types/nutrition'
import { api, type Paginated } from './api'
import { cleanParams } from './download'

export const seasonService = {
  list: async () => (await api.get<Season[]>('/seasons/')).data,
  current: async (farm?: number | null) => (await api.get<CurrentSeason>('/seasons/current/', { params: cleanParams({ farm }) })).data,
}

export const availabilityService = {
  list: async (params: { farm?: number | null; season?: number | null }) =>
    (await api.get<IngredientAvailability[]>('/ingredient-availability/', { params: cleanParams(params) })).data,
  create: async (payload: { farm: number; ingredient: number; season: number; level: AvailabilityLevel }) =>
    (await api.post<IngredientAvailability>('/ingredient-availability/', payload)).data,
  update: async (id: number, level: AvailabilityLevel) =>
    (await api.patch<IngredientAvailability>(`/ingredient-availability/${id}/`, { level })).data,
  remove: async (id: number) => {
    await api.delete(`/ingredient-availability/${id}/`)
  },
}

export const adviceService = {
  list: async (params: { season?: number | null }) =>
    (await api.get<Paginated<SeasonalAdvice>>('/seasonal-advice/', { params: cleanParams({ ...params, page_size: 100 }) })).data.results,
  create: async (payload: { season: number; topic: string; title: string; text: string; source?: number | null }) =>
    (await api.post<SeasonalAdvice>('/seasonal-advice/', payload)).data,
  transition: async (id: number, action: WorkflowAction, comment = '') =>
    (await api.post<SeasonalAdvice>(`/seasonal-advice/${id}/${action}/`, { comment })).data,
}
