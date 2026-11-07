import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { breeder, fakeAuth, renderWithProviders } from '@/test/utils'
import { GuestRoute, ProtectedRoute, RoleRoute } from './guards'

const login = { path: '/connexion', element: <p>Page de connexion</p> }
const home = { path: '/', element: <p>Accueil</p> }

describe('protection des routes', () => {
  it('redirige un visiteur non connecté vers la connexion', () => {
    renderWithProviders(<ProtectedRoute><p>Secret</p></ProtectedRoute>, { route: '/parametres', extraRoutes: [login] })
    expect(screen.getByText('Page de connexion')).toBeInTheDocument()
    expect(screen.queryByText('Secret')).not.toBeInTheDocument()
  })

  it('affiche un chargement pendant la restauration de session', () => {
    renderWithProviders(<ProtectedRoute><p>Secret</p></ProtectedRoute>, { auth: fakeAuth({ status: 'loading' }), route: '/parametres' })
    expect(screen.getByRole('status')).toHaveTextContent(/Chargement/)
  })

  it('laisse passer un utilisateur connecté', () => {
    renderWithProviders(<ProtectedRoute><p>Secret</p></ProtectedRoute>, {
      auth: fakeAuth({ status: 'authenticated', user: breeder }),
      route: '/parametres',
    })
    expect(screen.getByText('Secret')).toBeInTheDocument()
  })

  it("refuse l'espace administrateur à un éleveur", () => {
    renderWithProviders(<RoleRoute roles={['ADMIN']}><p>Admin</p></RoleRoute>, {
      auth: fakeAuth({ status: 'authenticated', user: breeder }),
      route: '/administration/utilisateurs',
      extraRoutes: [home],
    })
    expect(screen.getByText('Accueil')).toBeInTheDocument()
    expect(screen.queryByText('Admin')).not.toBeInTheDocument()
  })

  it("ouvre l'espace administrateur à un administrateur", () => {
    const admin = { ...breeder, role: 'ADMIN' as const, is_platform_admin: true }
    renderWithProviders(<RoleRoute roles={['ADMIN']}><p>Admin</p></RoleRoute>, {
      auth: fakeAuth({ status: 'authenticated', user: admin }),
      route: '/administration/utilisateurs',
    })
    expect(screen.getByText('Admin')).toBeInTheDocument()
  })

  it('renvoie un utilisateur déjà connecté hors de la page de connexion', () => {
    renderWithProviders(<GuestRoute><p>Formulaire</p></GuestRoute>, {
      auth: fakeAuth({ status: 'authenticated', user: breeder }),
      route: '/connexion',
      extraRoutes: [home],
    })
    expect(screen.getByText('Accueil')).toBeInTheDocument()
  })
})
