import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/services/api'
import { fakeAuth, renderWithProviders } from '@/test/utils'
import { RegisterPage } from './RegisterPage'

async function fillForm(password = 'Brebis-Touabire-2026', confirm = password) {
  await userEvent.type(screen.getByLabelText(/^Prénom/), 'Awa')
  await userEvent.type(screen.getByLabelText(/^Nom\*?$/), 'Ndiaye')
  await userEvent.type(screen.getByLabelText(/Adresse e-mail/), 'awa@exemple.sn')
  await userEvent.type(screen.getByLabelText(/Nom de l'exploitation/), 'Bergerie de Kaolack')
  await userEvent.type(screen.getByLabelText(/^Mot de passe/), password)
  await userEvent.type(screen.getByLabelText(/Confirmer le mot de passe/), confirm)
}

describe('RegisterPage', () => {
  it('refuse deux mots de passe différents', async () => {
    const auth = fakeAuth()
    renderWithProviders(<RegisterPage />, { auth, route: '/inscription' })
    await fillForm('Brebis-Touabire-2026', 'Autre-chose-2026')
    await userEvent.click(screen.getByRole('button', { name: 'Créer mon compte' }))
    expect(await screen.findByText('Les deux mots de passe ne correspondent pas.')).toBeInTheDocument()
    expect(auth.register).not.toHaveBeenCalled()
  })

  it('rattache les erreurs du serveur au bon champ', async () => {
    const auth = fakeAuth({
      register: vi
        .fn()
        .mockRejectedValue(
          new ApiError('Les données envoyées sont invalides.', 400, 'validation_error', {
            email: ['Un compte existe déjà avec cette adresse e-mail.'],
          }),
        ),
    })
    renderWithProviders(<RegisterPage />, { auth, route: '/inscription' })
    await fillForm()
    await userEvent.click(screen.getByRole('button', { name: 'Créer mon compte' }))
    expect(await screen.findByText('Un compte existe déjà avec cette adresse e-mail.')).toBeInTheDocument()
    expect(screen.getByLabelText(/Adresse e-mail/)).toHaveAttribute('aria-invalid', 'true')
  })

  it("envoie les informations de l'exploitation avec le compte", async () => {
    const auth = fakeAuth({ register: vi.fn().mockResolvedValue({}) })
    renderWithProviders(<RegisterPage />, { auth, route: '/inscription', extraRoutes: [{ path: '/', element: <p>ok</p> }] })
    await fillForm()
    await userEvent.click(screen.getByRole('button', { name: 'Créer mon compte' }))
    expect(auth.register).toHaveBeenCalledWith(expect.objectContaining({ email: 'awa@exemple.sn', farm_name: 'Bergerie de Kaolack' }))
  })
})
