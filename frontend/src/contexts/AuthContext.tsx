import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { onSessionExpired, refreshAccessToken } from '@/services/api'
import { authService } from '@/services/auth'
import { tokenStore } from '@/services/tokens'
import type { RegisterPayload, User } from '@/types/auth'
import { AuthContext, type AuthContextValue, type AuthStatus } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUserState] = useState<User | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [sessionExpired, setSessionExpired] = useState(false)

  const endSession = useCallback(
    (expired: boolean) => {
      tokenStore.clear()
      queryClient.clear()
      setUserState(null)
      setStatus('anonymous')
      setSessionExpired(expired)
    },
    [queryClient],
  )

  // Restauration de la session au chargement de la page (jeton de rafraîchissement stocké).
  useEffect(() => {
    let cancelled = false
    async function restore() {
      if (!tokenStore.getRefresh()) {
        setStatus('anonymous')
        return
      }
      try {
        await refreshAccessToken()
        const me = await authService.me()
        if (!cancelled) {
          setUserState(me)
          setStatus('authenticated')
        }
      } catch {
        if (!cancelled) endSession(false)
      }
    }
    restore()
    return () => {
      cancelled = true
    }
  }, [endSession])

  useEffect(() => onSessionExpired(() => endSession(true)), [endSession])

  const login = useCallback(async (email: string, password: string, remember: boolean) => {
    const result = await authService.login(email, password)
    tokenStore.setTokens(result.access, result.refresh, remember)
    setUserState(result.user)
    setStatus('authenticated')
    setSessionExpired(false)
    return result.user
  }, [])

  const register = useCallback(async (payload: RegisterPayload) => {
    const result = await authService.register(payload)
    tokenStore.setTokens(result.access, result.refresh, false)
    setUserState(result.user)
    setStatus('authenticated')
    setSessionExpired(false)
    return result.user
  }, [])

  const logout = useCallback(async () => {
    const refresh = tokenStore.getRefresh()
    try {
      if (refresh) await authService.logout(refresh)
    } catch {
      // Même si le serveur est injoignable, la session locale est effacée.
    } finally {
      endSession(false)
    }
  }, [endSession])

  const reloadUser = useCallback(async () => {
    setUserState(await authService.me())
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, sessionExpired, login, register, logout, setUser: setUserState, reloadUser }),
    [status, user, sessionExpired, login, register, logout, reloadUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
