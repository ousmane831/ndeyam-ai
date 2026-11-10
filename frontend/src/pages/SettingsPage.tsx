import { OfflinePanel } from '@/features/offline/OfflinePanel'
import { AlertRulesPanel } from '@/features/settings/AlertRulesPanel'
import { FarmsPanel } from '@/features/settings/FarmsPanel'
import { PasswordForm } from '@/features/settings/PasswordForm'
import { ProfileForm } from '@/features/settings/ProfileForm'

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Paramètres</h1>
        <p className="mt-1 text-sm text-slate-500">Profil, exploitations, réglages des alertes, hors ligne et sécurité du compte.</p>
      </div>
      <ProfileForm />
      <FarmsPanel />
      <AlertRulesPanel />
      <OfflinePanel />
      <PasswordForm />
    </div>
  )
}
