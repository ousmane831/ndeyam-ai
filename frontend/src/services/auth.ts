import type { AuthTokens, RegisterPayload, User } from '@/types/auth'
import { api } from './api'

export interface LoginResponse extends AuthTokens {
  user: User
}

export const authService = {
  async login(email: string, password: string): Promise<LoginResponse> {
    const { data } = await api.post<LoginResponse>('/auth/login/', { email, password })
    return data
  },

  async register(payload: RegisterPayload): Promise<LoginResponse> {
    const { data } = await api.post<LoginResponse>('/auth/register/', payload)
    return data
  },

  async logout(refresh: string): Promise<void> {
    await api.post('/auth/logout/', { refresh })
  },

  async me(): Promise<User> {
    const { data } = await api.get<User>('/auth/me/')
    return data
  },

  async updateProfile(payload: Pick<User, 'first_name' | 'last_name' | 'phone'>): Promise<User> {
    const { data } = await api.patch<User>('/auth/me/', payload)
    return data
  },

  async changePassword(current_password: string, new_password: string): Promise<string> {
    const { data } = await api.post<{ detail: string }>('/auth/change-password/', { current_password, new_password })
    return data.detail
  },

  async requestPasswordReset(email: string): Promise<string> {
    const { data } = await api.post<{ detail: string }>('/auth/password-reset/', { email })
    return data.detail
  },

  async confirmPasswordReset(uid: string, token: string, new_password: string): Promise<string> {
    const { data } = await api.post<{ detail: string }>('/auth/password-reset/confirm/', { uid, token, new_password })
    return data.detail
  },
}
