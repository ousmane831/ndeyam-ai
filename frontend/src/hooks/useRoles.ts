import { useAuth } from './useAuth'

/** Rôles utiles à l'affichage. Les droits réels sont toujours vérifiés par l'API. */
export function useRoles() {
  const { user } = useAuth()
  const isAdmin = Boolean(user?.is_platform_admin)
  return {
    isAdmin,
    isExpert: user?.role === 'EXPERT',
    /** Expert ou administrateur : gère et valide le référentiel. */
    isReviewer: isAdmin || user?.role === 'EXPERT',
  }
}
