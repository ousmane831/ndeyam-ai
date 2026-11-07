import { createContext } from 'react'
import type { RegisterPayload, User } from '@/types/auth'

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

export interface AuthContextValue {
  status: AuthStatus
  user: User | null
  /** Vrai si la dernière session s'est terminée par expiration (et non par déconnexion volontaire). */
  sessionExpired: boolean
  login: (email: string, password: string, remember: boolean) => Promise<User>
  register: (payload: RegisterPayload) => Promise<User>
  logout: () => Promise<void>
  setUser: (user: User) => void
  reloadUser: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
