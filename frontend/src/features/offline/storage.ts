/**
 * Stockage local du mode hors ligne. Les données d'un utilisateur ne sont gardées sur l'appareil que s'il a
 * choisi « Rester connecté » (même emplacement que son jeton de rafraîchissement) ; sinon elles disparaissent
 * avec l'onglet. Seule la file des saisies en attente est toujours conservée : on ne perd jamais une pesée.
 */
const REFRESH_KEY = 'ndeyam.refresh'

function area(kind: 'local' | 'session'): Storage | null {
  try {
    return kind === 'local' ? window.localStorage : window.sessionStorage
  } catch {
    return null
  }
}

/** Emplacement des données de session : celui du jeton de rafraîchissement. */
export function sessionArea(): Storage | null {
  return area('local')?.getItem(REFRESH_KEY) != null ? area('local') : area('session')
}

export function readJson<T>(key: string, fallback: T, where: Storage | null = sessionArea()): T {
  try {
    const raw = where?.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

/** Écrit une valeur ; renvoie false si l'appareil refuse (quota plein, navigation privée). */
export function writeJson(key: string, value: unknown, where: Storage | null = sessionArea()): boolean {
  try {
    where?.setItem(key, JSON.stringify(value))
    return Boolean(where)
  } catch {
    return false
  }
}

export function removeKey(key: string) {
  for (const kind of ['local', 'session'] as const) {
    try {
      area(kind)?.removeItem(key)
    } catch {
      /* rien à faire */
    }
  }
}

/** Efface les données de session hors ligne (cache, paquets de calcul, utilisateur), jamais la file d'envoi. */
export function clearSessionData() {
  for (const kind of ['local', 'session'] as const) {
    const store = area(kind)
    if (!store) continue
    try {
      for (const key of Object.keys(store)) {
        if (/^ndeyam\.(cache|pack|user|offline-results)\b/.test(key)) store.removeItem(key)
      }
    } catch {
      /* rien à faire */
    }
  }
}

export const localArea = () => area('local')
