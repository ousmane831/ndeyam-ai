/**
 * Stockage des jetons JWT.
 *
 * - Jeton d'accès (15 min) : uniquement en mémoire, jamais écrit sur le disque.
 * - Jeton de rafraîchissement : localStorage si « Rester connecté », sinon sessionStorage
 *   (effacé à la fermeture du navigateur). Il est révoqué côté serveur à la déconnexion.
 */
const REFRESH_KEY = 'ndeyam.refresh'

let accessToken: string | null = null

function safeStorage(kind: 'local' | 'session'): Storage | null {
  try {
    return kind === 'local' ? window.localStorage : window.sessionStorage
  } catch {
    return null
  }
}

export const tokenStore = {
  getAccess(): string | null {
    return accessToken
  },

  getRefresh(): string | null {
    return safeStorage('session')?.getItem(REFRESH_KEY) ?? safeStorage('local')?.getItem(REFRESH_KEY) ?? null
  },

  /** Enregistre une nouvelle paire. `remember` n'est pris en compte qu'à la connexion. */
  setTokens(access: string, refresh: string, remember?: boolean) {
    accessToken = access
    const persistent = remember ?? safeStorage('local')?.getItem(REFRESH_KEY) != null
    const target = safeStorage(persistent ? 'local' : 'session')
    const other = safeStorage(persistent ? 'session' : 'local')
    other?.removeItem(REFRESH_KEY)
    target?.setItem(REFRESH_KEY, refresh)
  },

  clear() {
    accessToken = null
    safeStorage('local')?.removeItem(REFRESH_KEY)
    safeStorage('session')?.removeItem(REFRESH_KEY)
  },
}
