import { RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Feedback'
import { useFarm } from '@/hooks/useFarm'
import { formatDateTime } from '@/utils/format'
import { useOnline } from './connectivity'
import { useOutbox } from './outbox'
import { downloadPack, loadPack } from './pack'

/** Mesures sur la version de production (compression standard d'un serveur web), novembre 2026. */
const USAGE = [
  ['Première ouverture (installation, une fois par version)', '≈ 530 Ko'],
  ['Ouverture suivante de l’application', '≈ 10 à 30 Ko'],
  ['Chaque écran consulté', '≈ 4 à 5 Ko'],
  ['Données de calcul hors ligne (par exploitation)', '≈ 2 à 20 Ko'],
  ['Envoi d’une séance de pesée ou d’un calcul', '≈ 1 à 7 Ko'],
] as const

/** Paramètres : ce qui est gardé sur l'appareil, ce qui attend d'être envoyé, et la consommation de données. */
export function OfflinePanel() {
  const online = useOnline()
  const pending = useOutbox()
  const { writableFarms } = useFarm()
  const [, setTick] = useState(0)
  const [busy, setBusy] = useState(false)

  const refresh = async () => {
    setBusy(true)
    try {
      await Promise.allSettled(writableFarms.map((f) => downloadPack(f.id)))
    } finally {
      setBusy(false)
      setTick((t) => t + 1)
    }
  }

  return (
    <Card title="Hors ligne et consommation de données">
      <div className="space-y-5 text-sm text-slate-700">
        <p>
          Sans réseau, l'application se rouvre avec les données déjà consultées. Les pesées et les calculs de ration
          (formule rapide) restent possibles : ils sont gardés sur cet appareil puis envoyés au retour du réseau. Un calcul
          fait hors ligne est provisoire : le serveur le recalcule et l'enregistre, et seule une formule vérifiée par un
          expert peut nourrir des animaux.
        </p>
        {writableFarms.length > 0 && (
          <div>
            <h3 className="font-semibold text-slate-900">Données de calcul sur cet appareil</h3>
            <ul className="mt-2 space-y-1">
              {writableFarms.map((f) => {
                const pack = loadPack(f.id)
                return (
                  <li key={f.id} className="flex flex-wrap justify-between gap-2">
                    <span>{f.name}</span>
                    <span className="text-slate-500">{pack ? `à jour du ${formatDateTime(pack.generated_at)}` : 'pas encore téléchargées'}</span>
                  </li>
                )
              })}
            </ul>
            <Button variant="secondary" size="sm" className="mt-3" icon={<RefreshCw className="size-4" />} loading={busy} disabled={!online} onClick={refresh}>
              Mettre à jour maintenant
            </Button>
          </div>
        )}
        <p><strong className="font-semibold">Saisies en attente d'envoi :</strong> {pending.length === 0 ? 'aucune' : pending.length}</p>
        <div>
          <h3 className="font-semibold text-slate-900">Consommation de données (mesurée)</h3>
          <dl className="mt-2 divide-y divide-slate-100">
            {USAGE.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4 py-1.5"><dt>{label}</dt><dd className="font-medium whitespace-nowrap tabular-nums">{value}</dd></div>
            ))}
          </dl>
          <p className="mt-2 text-xs text-slate-500">Une semaine d'usage quotidien (une séance de pesée et une dizaine d'écrans par jour) consomme moins de 1 Mo.</p>
        </div>
      </div>
    </Card>
  )
}
