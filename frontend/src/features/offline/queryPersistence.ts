import { dehydrate, hydrate, type DehydratedState, type QueryClient } from '@tanstack/react-query'
import type { User } from '@/types/auth'
import { readJson, writeJson } from './storage'

/**
 * Copie locale des données déjà consultées (listes d'animaux, lots, pesées, formules…) pour les relire
 * sans connexion. Rattachée à l'utilisateur, limitée à 7 jours et à ~3 Mo ; effacée à la déconnexion.
 */
const MAX_AGE_MS = 7 * 24 * 3600 * 1000
const MAX_CHARS = 3_000_000
const SKIP = new Set(['health', 'assistant', 'assistant-status', 'documents-search'])
const cacheKey = (userId: number) => `ndeyam.cache.${userId}`

export function restoreQueries(client: QueryClient, userId: number) {
  const saved = readJson<{ savedAt: number; state: DehydratedState } | null>(cacheKey(userId), null)
  if (saved && Date.now() - saved.savedAt < MAX_AGE_MS) hydrate(client, saved.state)
}

export function persistQueries(client: QueryClient, userId: number): () => void {
  let timer: ReturnType<typeof setTimeout> | null = null
  const flush = () => {
    const state = dehydrate(client, {
      shouldDehydrateQuery: (q) => q.state.status === 'success' && !SKIP.has(String(q.queryKey[0])),
    })
    const json = JSON.stringify({ savedAt: Date.now(), state })
    if (json.length <= MAX_CHARS) writeJson(cacheKey(userId), JSON.parse(json))
  }
  let dirty = false
  const flushIfDirty = () => {
    if (timer) clearTimeout(timer)
    timer = null
    if (dirty) flush()
    dirty = false
  }
  const unsubscribe = client.getQueryCache().subscribe((event) => {
    if (event.type !== 'updated' || event.action.type !== 'success') return
    dirty = true
    if (timer) clearTimeout(timer)
    timer = setTimeout(flushIfDirty, 1000)
  })
  // Page fermée ou mise en arrière-plan (téléphone verrouillé, autre application) : on écrit tout de suite.
  const onHide = () => {
    if (document.visibilityState === 'hidden') flushIfDirty()
  }
  window.addEventListener('pagehide', flushIfDirty)
  document.addEventListener('visibilitychange', onHide)
  return () => {
    // À la déconnexion, rien n'est réécrit : les données locales viennent d'être effacées.
    if (timer) clearTimeout(timer)
    window.removeEventListener('pagehide', flushIfDirty)
    document.removeEventListener('visibilitychange', onHide)
    unsubscribe()
  }
}

/** Dernier profil connu : permet de rouvrir l'application sans réseau (la session est revalidée au retour). */
export const saveUserSnapshot = (user: User) => writeJson('ndeyam.user', user)
export const loadUserSnapshot = () => readJson<User | null>('ndeyam.user', null)
