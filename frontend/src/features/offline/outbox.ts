import { useSyncExternalStore } from 'react'
import { ApiError } from '@/services/api'
import { weighingService } from '@/services/animals'
import { formulaService } from '@/services/formulas'
import type { CalculationPayload } from '@/types/formula'
import type { WeighingMethod } from '@/types/animal'
import { linkOfflineResult } from './offlineResults'
import { localArea, readJson, writeJson } from './storage'

/**
 * File des saisies faites sans connexion, envoyées dans l'ordre dès que le serveur répond.
 * Toujours conservée sur l'appareil (même sans « Rester connecté ») et rattachée à l'utilisateur :
 * une saisie n'est jamais perdue, ni envoyée sous le nom de quelqu'un d'autre.
 */
type WeighingPayload = { animal: number; weight_kg: string; weighed_on: string; method: WeighingMethod; observations?: string }
type SessionPayload = { weighed_on: string; method: WeighingMethod; entries: { animal: number; weight_kg: string }[] }

export type OutboxEntry =
  | { id: string; kind: 'weighing'; payload: WeighingPayload; label: string; createdAt: string; error?: string }
  | { id: string; kind: 'weighing-session'; payload: SessionPayload; label: string; createdAt: string; error?: string }
  | { id: string; kind: 'formula'; payload: CalculationPayload; label: string; createdAt: string; error?: string; localResultId: string }

type NewEntry = OutboxEntry extends infer E ? (E extends OutboxEntry ? Omit<E, 'id' | 'createdAt' | 'error'> : never) : never

let userId: number | null = null
let entries: OutboxEntry[] = []
const listeners = new Set<() => void>()
const key = () => `ndeyam.outbox.${userId}`
const emit = () => listeners.forEach((l) => l())
const save = () => {
  if (userId !== null) writeJson(key(), entries, localArea())
  emit()
}

export function setOutboxUser(id: number | null) {
  if (id === userId) return
  userId = id
  entries = id === null ? [] : readJson<OutboxEntry[]>(key(), [], localArea())
  emit()
}

export const outbox = {
  list: () => entries,
  add(entry: NewEntry): OutboxEntry {
    const full = { ...entry, id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, createdAt: new Date().toISOString() } as OutboxEntry
    entries = [...entries, full]
    save()
    return full
  },
  discard(id: string) {
    entries = entries.filter((e) => e.id !== id)
    save()
  },
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
}

export const isNetworkError = (e: unknown) => e instanceof ApiError && e.status === null

async function send(entry: OutboxEntry) {
  switch (entry.kind) {
    case 'weighing':
      await weighingService.create(entry.payload)
      return
    case 'weighing-session':
      await weighingService.bulk(entry.payload)
      return
    case 'formula': {
      const { formula } = await formulaService.calculate(entry.payload)
      if (formula) linkOfflineResult(entry.localResultId, formula.id)
    }
  }
}

let running: Promise<{ sent: number; failed: number }> | null = null

/**
 * Envoie les saisies en attente, dans l'ordre. Une erreur réseau arrête l'envoi (on réessaiera) ;
 * un refus du serveur (ex. pesée en double) est gardé avec son message, pour que l'éleveur décide.
 */
export function syncOutbox(): Promise<{ sent: number; failed: number }> {
  if (running) return running
  running = (async () => {
    let sent = 0
    let failed = 0
    for (const entry of [...entries]) {
      if (entry.error) continue
      try {
        await send(entry)
        entries = entries.filter((e) => e.id !== entry.id)
        sent += 1
        save()
      } catch (e) {
        if (isNetworkError(e)) break
        failed += 1
        const message = e instanceof ApiError ? [e.message, ...Object.values(e.fieldErrors).flat()].join(' ') : 'Envoi refusé.'
        entries = entries.map((x) => (x.id === entry.id ? { ...x, error: message } : x))
        save()
      }
    }
    return { sent, failed }
  })().finally(() => {
    running = null
    emit()
  })
  emit()
  return running
}

/** Vrai pendant un envoi. */
export function useSyncing(): boolean {
  return useSyncExternalStore(outbox.subscribe, () => running !== null, () => false)
}

export function useOutbox(): OutboxEntry[] {
  return useSyncExternalStore(outbox.subscribe, outbox.list, outbox.list)
}
