import type { AdminUser, UserRole } from '@/types/auth'
import { api, type Paginated } from './api'

export interface AdminUserFilters {
  page?: number
  search?: string
  role?: UserRole | ''
  is_active?: 'true' | 'false' | ''
}

export interface AdminUserCreatePayload {
  email: string
  password: string
  first_name: string
  last_name: string
  phone?: string
  role: UserRole
}

export const adminUserService = {
  async list(filters: AdminUserFilters): Promise<Paginated<AdminUser>> {
    const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== '' && value != null))
    const { data } = await api.get<Paginated<AdminUser>>('/admin/users/', { params })
    return data
  },

  async create(payload: AdminUserCreatePayload): Promise<AdminUser> {
    const { data } = await api.post<AdminUser>('/admin/users/', payload)
    return data
  },

  async update(id: number, payload: Partial<Pick<AdminUser, 'role' | 'is_active'>>): Promise<AdminUser> {
    const { data } = await api.patch<AdminUser>(`/admin/users/${id}/`, payload)
    return data
  },
}
