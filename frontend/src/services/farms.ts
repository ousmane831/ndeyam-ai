import type { MembershipRole } from '@/types/auth'
import type { Farm, FarmMember } from '@/types/farm'
import { api, type Paginated } from './api'

export type FarmPayload = Pick<Farm, 'name' | 'region' | 'locality' | 'description'> & { country?: string }

export const farmService = {
  async list(): Promise<Paginated<Farm>> {
    const { data } = await api.get<Paginated<Farm>>('/farms/', { params: { page_size: 100 } })
    return data
  },

  async create(payload: FarmPayload): Promise<Farm> {
    const { data } = await api.post<Farm>('/farms/', payload)
    return data
  },

  async update(id: number, payload: Partial<FarmPayload>): Promise<Farm> {
    const { data } = await api.patch<Farm>(`/farms/${id}/`, payload)
    return data
  },

  async members(farmId: number): Promise<FarmMember[]> {
    const { data } = await api.get<FarmMember[]>(`/farms/${farmId}/members/`)
    return data
  },

  async addMember(farmId: number, email: string, role: Exclude<MembershipRole, 'OWNER'>): Promise<FarmMember> {
    const { data } = await api.post<FarmMember>(`/farms/${farmId}/members/`, { email, role })
    return data
  },

  async removeMember(farmId: number, membershipId: number): Promise<void> {
    await api.delete(`/farms/${farmId}/members/${membershipId}/`)
  },
}
