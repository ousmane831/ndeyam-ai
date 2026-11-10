import { RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Feedback'
import { useFarm } from '@/hooks/useFarm'
import { tk } from '@/i18n'
import { formatDateTime } from '@/utils/format'
import { useOnline } from './connectivity'
import { useOutbox } from './outbox'
import { downloadPack, loadPack } from './pack'

/** Mesures sur la version de production (compression standard d'un serveur web), novembre 2026. */
const USAGE = [
  [tk('Première ouverture (installation, une fois par version)'), tk('≈ 600 Ko')],
  [tk('Ouverture suivante de l’application'), tk('≈ 10 à 30 Ko')],
  [tk('Chaque écran consulté'), tk('≈ 4 à 5 Ko')],
  [tk('Données de calcul hors ligne (par exploitation)'), tk('≈ 2 à 20 Ko')],
  [tk('Envoi d’une séance de pesée ou d’un calcul'), tk('≈ 1 à 7 Ko')],
] as const

/** Paramètres : ce qui est gardé sur l'appareil, ce qui attend d'être envoyé, et la consommation de données. */
export function OfflinePanel() {
  const { t } = useTranslation()
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
      setTick((n) => n + 1)
    }
  }

  return (
    <Card title={t('Hors ligne et consommation de données')}>
      <div className="space-y-5 text-sm text-slate-700">
        <p>
          {t(
            "Sans réseau, l'application se rouvre avec les données déjà consultées. Les pesées et les calculs de ration (formule rapide) restent possibles : ils sont gardés sur cet appareil puis envoyés au retour du réseau. Un calcul fait hors ligne est provisoire : le serveur le recalcule et l'enregistre, et seule une formule vérifiée par un expert peut nourrir des animaux.",
          )}
        </p>
        {writableFarms.length > 0 && (
          <div>
            <h3 className="font-semibold text-slate-900">{t('Données de calcul sur cet appareil')}</h3>
            <ul className="mt-2 space-y-1">
              {writableFarms.map((f) => {
                const pack = loadPack(f.id)
                return (
                  <li key={f.id} className="flex flex-wrap justify-between gap-2">
                    <span>{f.name}</span>
                    <span className="text-slate-500">{pack ? t('à jour du {{date}}', { date: formatDateTime(pack.generated_at) }) : t('pas encore téléchargées')}</span>
                  </li>
                )
              })}
            </ul>
            <Button variant="secondary" size="sm" className="mt-3" icon={<RefreshCw className="size-4" />} loading={busy} disabled={!online} onClick={refresh}>
              {t('Mettre à jour maintenant')}
            </Button>
          </div>
        )}
        <p><strong className="font-semibold">{t("Saisies en attente d'envoi :")}</strong> {pending.length === 0 ? t('aucune') : pending.length}</p>
        <div>
          <h3 className="font-semibold text-slate-900">{t('Consommation de données (mesurée)')}</h3>
          <dl className="mt-2 divide-y divide-slate-100">
            {USAGE.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4 py-1.5"><dt>{t(label)}</dt><dd className="font-medium whitespace-nowrap tabular-nums">{t(value)}</dd></div>
            ))}
          </dl>
          <p className="mt-2 text-xs text-slate-500">{t("Une semaine d'usage quotidien (une séance de pesée et une dizaine d'écrans par jour) consomme moins de 1 Mo.")}</p>
        </div>
      </div>
    </Card>
  )
}
