import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'
import { Spinner } from '@/components/ui/Spinner'
import { useAuth } from '@/hooks/useAuth'
import type { UserRole } from '@/types/auth'

function FullPageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner label="Chargement de votre session…" />
    </div>
  )
}

/** Réservé aux utilisateurs connectés ; sinon redirection vers la connexion (avec retour prévu). */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <FullPageLoader />
  if (status === 'anonymous') {
    return <Navigate to="/connexion" replace state={{ from: `${location.pathname}${location.search}` }} />
  }
  return children
}

/** Pages publiques (connexion, inscription) : un utilisateur déjà connecté est renvoyé au tableau de bord. */
export function GuestRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  if (status === 'loading') return <FullPageLoader />
  if (status === 'authenticated') return <Navigate to="/" replace />
  return children
}

/** Restreint une page à certains rôles. L'API applique toujours ses propres contrôles. */
export function RoleRoute({ roles, children }: { roles: UserRole[]; children: ReactNode }) {
  const { user } = useAuth()
  if (!user) return null
  const allowed = user.is_platform_admin ? roles.includes('ADMIN') || roles.includes(user.role) : roles.includes(user.role)
  if (!allowed) return <Navigate to="/" replace />
  return children
}
