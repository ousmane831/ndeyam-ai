import { Smartphone } from 'lucide-react'
import { useInstallPrompt } from './useInstallPrompt'

/** « Installer l'application » : une icône sur l'écran d'accueil du téléphone, sans passer par un magasin d'applications. */
export function InstallAppButton() {
  const { canInstall, install } = useInstallPrompt()
  if (!canInstall) return null
  return (
    <button type="button" onClick={install}
      className="mx-3 mt-3 flex min-h-11 items-center gap-2 rounded-md bg-mil-400 px-3 text-sm font-semibold text-brand-900 hover:bg-mil-300">
      <Smartphone className="size-5" aria-hidden /> Installer l'application
    </button>
  )
}
