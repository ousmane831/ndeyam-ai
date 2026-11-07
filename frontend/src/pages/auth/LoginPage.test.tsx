import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/services/api'
import { breeder, fakeAuth, renderWithProviders } from '@/test/utils'
import { LoginPage } from './LoginPage'

const home = { path: '/', element: <p>Accueil connecté</p> }

describe('LoginPage', () => {
  it("valide les champs avant d'appeler l'API", async () => {
    const auth = fakeAuth()
    renderWithProviders(<LoginPage />, { auth, route: '/connexion' })
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }))
    expect(await screen.findByText('Saisissez une adresse e-mail valide.')).toBeInTheDocument()
    expect(screen.getByText('Saisissez votre mot de passe.')).toBeInTheDocument()
    expect(auth.login).not.toHaveBeenCalled()
  })

  it("affiche l'erreur renvoyée par le serveur", async () => {
    const auth = fakeAuth({
      login: vi.fn().mockRejectedValue(new ApiError('Adresse e-mail ou mot de passe incorrect, ou compte désactivé.', 401, 'no_active_account')),
    })
    renderWithProviders(<LoginPage />, { auth, route: '/connexion' })
    await userEvent.type(screen.getByLabelText(/Adresse e-mail/), 'awa@exemple.sn')
    await userEvent.type(screen.getByLabelText(/^Mot de passe/), 'mauvais')
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }))
    expect(await screen.findByText(/mot de passe incorrect/)).toBeInTheDocument()
  })

  it('connecte avec « Rester connecté » puis redirige', async () => {
    const auth = fakeAuth({ login: vi.fn().mockResolvedValue(breeder) })
    renderWithProviders(<LoginPage />, { auth, route: '/connexion', extraRoutes: [home] })
    await userEvent.type(screen.getByLabelText(/Adresse e-mail/), 'awa@exemple.sn')
    await userEvent.type(screen.getByLabelText(/^Mot de passe/), 'Brebis-Touabire-2026')
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }))
    expect(auth.login).toHaveBeenCalledWith('awa@exemple.sn', 'Brebis-Touabire-2026', true)
    expect(await screen.findByText('Accueil connecté')).toBeInTheDocument()
  })

  it("prévient l'utilisateur lorsque sa session a expiré", () => {
    renderWithProviders(<LoginPage />, { auth: fakeAuth({ sessionExpired: true }), route: '/connexion' })
    expect(screen.getByText(/session a expiré/)).toBeInTheDocument()
  })
})
