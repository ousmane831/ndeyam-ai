import { onlineManager } from '@tanstack/react-query'
import { useSyncExternalStore } from 'react'

/**
 * État de connexion. Le navigateur peut se croire en ligne alors que le serveur est injoignable (réseau
 * sans Internet) : un échec réseau d'une requête bascule l'application hors ligne, puis une sonde légère
 * (/health/) vérifie toutes les 15 secondes si le serveur répond à nouveau. Hors ligne, TanStack Query met
 * les requêtes en pause au lieu d'échouer : les données déjà chargées restent affichées.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
const PROBE_MS = 15_000
let probe: ReturnType<typeof setInterval> | null = null

async function serverAnswers(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/health/`, { cache: 'no-store' })
    return res.status < 500 || res.status === 503
  } catch {
    return false
  }
}

function startProbe() {
  if (probe) return
  probe = setInterval(async () => {
    if (await serverAnswers()) setOnline(true)
  }, PROBE_MS)
}

export function setOnline(online: boolean) {
  if (online && probe) {
    clearInterval(probe)
    probe = null
  }
  onlineManager.setOnline(online)
  if (!online) startProbe()
}

/** Appelé par le client HTTP quand une requête n'obtient aucune réponse. */
export function reportNetworkFailure() {
  if (onlineManager.isOnline()) setOnline(false)
}

export const isOnline = () => onlineManager.isOnline()

export function useOnline(): boolean {
  return useSyncExternalStore((cb) => onlineManager.subscribe(cb), () => onlineManager.isOnline(), () => true)
}
