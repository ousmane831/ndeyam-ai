import type { Alert, AlertRule, AlertRuleDefinition } from '@/types/alert'
import type { DashboardData } from '@/types/dashboard'
import { api, type Paginated } from './api'
import { cleanParams } from './download'

export interface AlertFilters {
  farm?: number | null
  page?: number
  status?: string
  severity?: string
  alert_type?: string
  animal?: number
}

export const alertService = {
  list: async (filters: AlertFilters) =>
    (await api.get<Paginated<Alert>>('/alerts/', { params: cleanParams(filters) })).data,
  act: async (id: number, action: 'acknowledge' | 'resolve' | 'dismiss', note = '') =>
    (await api.post<Alert>(`/alerts/${id}/${action}/`, { note })).data,
  evaluate: async (farm?: number | null) =>
    (await api.post<{ created: number; updated: number; resolved: number }>('/alerts/evaluate/', cleanParams({ farm }))).data,
  rules: async () => (await api.get<AlertRule[]>('/alert-rules/')).data,
  definitions: async () => (await api.get<AlertRuleDefinition[]>('/alert-rules/definitions/')).data,
  saveRule: async (rule: { id?: number; farm: number; alert_type: string; parameters: Record<string, number>; is_active: boolean }) =>
    rule.id
      ? (await api.patch<AlertRule>(`/alert-rules/${rule.id}/`, { parameters: rule.parameters, is_active: rule.is_active })).data
      : (await api.post<AlertRule>('/alert-rules/', rule)).data,
}

export const dashboardService = {
  get: async (farm?: number | null) => (await api.get<DashboardData>('/dashboard/', { params: cleanParams({ farm }) })).data,
}
