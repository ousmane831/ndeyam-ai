import { useQueryClient } from '@tanstack/react-query'
import { CloudOff, RefreshCw, TriangleAlert } from 'lucide-react'
import { useCallback, useEffect } from 'react'
import { useFarm } from '@/hooks/useFarm'
import { useOnline } from './connectivity'
import { outbox, syncOutbox, useOutbox, useSyncing } from './outbox'
import { downloadPack } from './pack'

const REFRESHED_AFTER_SYNC = ['animals', 'growth', 'weighings', 'group-growth', 'alerts', 'dashboard', 'formulas', 'formula']

/**
 * Bandeau de connexion et synchronisation : télécharge le paquet de calcul hors ligne de chaque exploitation
 * (quelques Ko) quand le réseau est là, envoie les saisies en attente dès que le serveur répond.
 */
export function OfflineSync() {
  const online = useOnline()
  const entries = useOutbox()
  const queryClient = useQueryClient()
  const { writableFarms } = useFarm()
  const busy = useSyncing()
  const waiting = entries.filter((e) => !e.error)
  const refused = entries.filter((e) => e.error)
  const farmIds = writableFarms.map((f) => f.id).join(',')

  useEffect(() => {
    if (!online || !farmIds) return
    for (const id of farmIds.split(',')) downloadPack(Number(id)).catch(() => { /* on réessaiera au prochain retour du réseau */ })
  }, [online, farmIds])

  const sync = useCallback(async () => {
    const { sent } = await syncOutbox()
    if (sent) REFRESHED_AFTER_SYNC.forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }))
  }, [queryClient])

  useEffect(() => {
    if (online && waiting.length > 0) void sync()
  }, [online, waiting.length, sync])

  if (online && entries.length === 0) return null
  return (
    <div className="space-y-2" role="status" aria-live="polite">
      {!online && (
        <div className="flex items-start gap-3 rounded-md border border-slate-300 bg-slate-800 px-4 py-3 text-sm text-white">
          <CloudOff className="mt-0.5 size-5 shrink-0 text-mil-300" aria-hidden />
          <p>
            <strong className="font-semibold">Hors ligne.</strong> Vous consultez les données gardées sur cet appareil.
            Les pesées et les calculs de ration restent possibles : ils seront envoyés au retour du réseau.
            {waiting.length > 0 && <span className="mt-1 block font-semibold text-mil-200">{waiting.length} saisie(s) en attente d'envoi.</span>}
          </p>
        </div>
      )}
      {online && waiting.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-md border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-800">
          <RefreshCw className={`size-4 ${busy ? 'animate-spin' : ''}`} aria-hidden />
          <span className="flex-1">{busy ? 'Envoi' : 'À envoyer'} : {waiting.length} saisie(s) faite(s) hors ligne.</span>
          {!busy && <button type="button" onClick={sync} className="min-h-10 rounded-md px-3 font-semibold underline">Envoyer maintenant</button>}
        </div>
      )}
      {refused.length > 0 && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <p className="flex items-center gap-2 font-semibold"><TriangleAlert className="size-4" aria-hidden /> Refusé par le serveur à l'envoi</p>
          <ul className="mt-2 space-y-2">
            {refused.map((e) => (
              <li key={e.id} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <span><strong>{e.label}</strong> : {e.error}</span>
                <button type="button" onClick={() => outbox.discard(e.id)} className="min-h-10 font-semibold underline">Retirer</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
