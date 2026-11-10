import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { setOutboxUser } from '@/features/offline/outbox'
import { resetOfflineResultsCache } from '@/features/offline/offlineResults'
import { loadUserSnapshot, persistQueries, restoreQueries, saveUserSnapshot } from '@/features/offline/queryPersistence'
import { onSessionExpired, refreshAccessToken, toApiError } from '@/services/api'
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
          restoreQueries(queryClient, me.id)
          setUserState(me)
          setStatus('authenticated')
        }
      } catch (error) {
        if (cancelled) return
        // Sans réseau, on rouvre la session avec le dernier profil connu et les données gardées sur
        // l'appareil ; le jeton est renouvelé automatiquement à la première requête, au retour du réseau.
        const snapshot = loadUserSnapshot()
        if (toApiError(error).status === null && snapshot) {
          restoreQueries(queryClient, snapshot.id)
          setUserState(snapshot)
          setStatus('authenticated')
        } else {
          endSession(false)
        }
      }
    }
    restore()
    return () => {
      cancelled = true
    }
  }, [endSession, queryClient])

  // Profil, file d'envoi et copie locale des données suivent l'utilisateur connecté.
  useEffect(() => {
    setOutboxUser(user?.id ?? null)
    resetOfflineResultsCache()
    if (!user) return
    saveUserSnapshot(user)
    return persistQueries(queryClient, user.id)
  }, [user, queryClient])

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
