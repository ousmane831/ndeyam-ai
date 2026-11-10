/**
 * Client HTTP centralisé.
 *
 * - Ajoute le jeton d'accès à chaque requête.
 * - Sur une réponse 401, renouvelle UNE seule fois le jeton (requêtes simultanées mutualisées)
 *   puis rejoue la requête ; en cas d'échec, la session est terminée proprement.
 * - Convertit toute erreur en `ApiError` avec un message en français.
 */
import axios, { AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import { reportNetworkFailure } from '@/features/offline/connectivity'
import { tokenStore } from './tokens'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

export interface ApiErrorBody {
  detail?: string
  code?: string
  errors?: Record<string, unknown>
}

export class ApiError extends Error {
  readonly status: number | null
  readonly code: string
  readonly fieldErrors: Record<string, string[]>

  constructor(message: string, status: number | null, code: string, fieldErrors: Record<string, string[]> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fieldErrors = fieldErrors
  }
}

/** Aplatit les messages d'erreur (listes, chaînes ou objets imbriqués, ex. erreurs par ligne). */
function flattenMessages(value: unknown): string[] {
  if (value === null || value === undefined) return []
  if (Array.isArray(value)) return value.flatMap(flattenMessages)
  if (typeof value === 'object') return Object.values(value as Record<string, unknown>).flatMap(flattenMessages)
  return [String(value)]
}

function normaliseFieldErrors(errors: ApiErrorBody['errors']): Record<string, string[]> {
  const result: Record<string, string[]> = {}
  for (const [field, value] of Object.entries(errors ?? {})) {
    result[field] = flattenMessages(value)
  }
  return result
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (axios.isAxiosError(error)) {
    const err = error as AxiosError<ApiErrorBody>
    if (!err.response) {
      reportNetworkFailure()
      return new ApiError(
        'Impossible de joindre le serveur. Vérifiez que le backend est démarré et votre connexion réseau.',
        null,
        'network_error',
      )
    }
    const body = err.response.data ?? {}
    const status = err.response.status
    const fallback =
      status >= 500
        ? 'Une erreur interne est survenue sur le serveur.'
        : status === 429
          ? 'Trop de tentatives. Patientez une minute avant de réessayer.'
          : 'La requête a échoué.'
    return new ApiError(body.detail || fallback, status, body.code || 'error', normaliseFieldErrors(body.errors))
  }
  return new ApiError('Une erreur inattendue est survenue.', null, 'unknown_error')
}

// --- Fin de session ---------------------------------------------------------------------

type SessionListener = () => void
const sessionListeners = new Set<SessionListener>()

/** Permet au contexte d'authentification d'être prévenu lorsque la session expire. */
export function onSessionExpired(listener: SessionListener): () => void {
  sessionListeners.add(listener)
  return () => sessionListeners.delete(listener)
}

// --- Renouvellement du jeton --------------------------------------------------------------

const NO_REFRESH_PATHS = ['/auth/login/', '/auth/register/', '/auth/refresh/', '/auth/password-reset/']
let refreshInFlight: Promise<string> | null = null

export async function refreshAccessToken(): Promise<string> {
  const refresh = tokenStore.getRefresh()
  if (!refresh) throw new ApiError('Session expirée. Veuillez vous reconnecter.', 401, 'session_expired')
  refreshInFlight ??= axios
    .post<{ access: string; refresh: string }>(`${BASE_URL}/auth/refresh/`, { refresh })
    .then(({ data }) => {
      tokenStore.setTokens(data.access, data.refresh)
      return data.access
    })
    .finally(() => {
      refreshInFlight = null
    })
  return refreshInFlight
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.getAccess()
  if (token) config.headers.set('Authorization', `Bearer ${token}`)
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401 && error.config) {
      const config = error.config as AxiosRequestConfig & { _retried?: boolean }
      const url = config.url ?? ''
      const eligible = !config._retried && !NO_REFRESH_PATHS.some((path) => url.includes(path))
      if (eligible && tokenStore.getRefresh()) {
        config._retried = true
        try {
          const access = await refreshAccessToken()
          config.headers = { ...(config.headers ?? {}), Authorization: `Bearer ${access}` }
          return api.request(config)
        } catch {
          tokenStore.clear()
          sessionListeners.forEach((listener) => listener())
          return Promise.reject(new ApiError('Votre session a expiré. Veuillez vous reconnecter.', 401, 'session_expired'))
        }
      }
    }
    return Promise.reject(toApiError(error))
  },
)

// --- Types communs ----------------------------------------------------------------------

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
