import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { assistantService } from '@/services/assistant'
import { breeder, fakeAuth, renderWithProviders } from '@/test/utils'
import { AssistantLauncher } from './AssistantLauncher'

const auth = () => fakeAuth({ status: 'authenticated', user: breeder })

describe('AssistantLauncher', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(assistantService, 'status').mockResolvedValue({
      configured: false, provider: null, model: null, message: "L'assistant IA n'est pas configuré (LLM_PROVIDER=none).",
    })
  })

  it("ouvre le panneau depuis le bouton flottant et le referme avec Échap", async () => {
    renderWithProviders(<AssistantLauncher />, { auth: auth() })
    const launcher = screen.getByRole('button', { name: "Ouvrir l'assistant Ndeyam AI" })
    expect(launcher).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await userEvent.click(launcher)
    expect(screen.getByRole('dialog', { name: 'Assistant Ndeyam AI' })).toBeInTheDocument()
    expect(await screen.findByText('Assistant non configuré')).toBeInTheDocument()
    expect(screen.getByLabelText('Votre question')).toBeDisabled()
    expect(screen.getByText(/ne pose aucun diagnostic vétérinaire/)).toBeInTheDocument()
    // Assistant non configuré : le champ est désactivé, le focus va sur « Fermer » (jamais hors du panneau).
    await vi.waitFor(() => expect(screen.getByRole('button', { name: "Fermer l'assistant" })).toHaveFocus())

    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it("propose la vue plein écran et se masque sur la page de l'assistant", async () => {
    const { unmount } = renderWithProviders(<AssistantLauncher />, { auth: auth() })
    await userEvent.click(screen.getByRole('button', { name: "Ouvrir l'assistant Ndeyam AI" }))
    expect(screen.getByRole('link', { name: /plein écran/ })).toHaveAttribute('href', '/assistant')
    unmount()

    renderWithProviders(<AssistantLauncher />, { auth: auth(), route: '/assistant' })
    expect(screen.queryByRole('button', { name: "Ouvrir l'assistant Ndeyam AI" })).not.toBeInTheDocument()
  })

  it('envoie une question depuis le panneau', async () => {
    vi.spyOn(assistantService, 'status').mockResolvedValue({ configured: true, provider: 'anthropic', model: 'claude-opus-5-5', message: '' })
    const create = vi.spyOn(assistantService, 'create').mockResolvedValue({
      id: 3, title: '', farm: 1, is_archived: false, messages_count: 0, created_at: '', updated_at: '',
    })
    const ask = vi.spyOn(assistantService, 'ask').mockResolvedValue([])
    vi.spyOn(assistantService, 'get').mockResolvedValue({
      id: 3, title: 'q', farm: 1, is_archived: false, messages_count: 0, created_at: '', updated_at: '', messages: [],
    })
    renderWithProviders(<AssistantLauncher />, { auth: auth() })
    await userEvent.click(screen.getByRole('button', { name: "Ouvrir l'assistant Ndeyam AI" }))
    const input = screen.getByLabelText('Votre question')
    await vi.waitFor(() => expect(input).toBeEnabled())
    await vi.waitFor(() => expect(input).toHaveFocus())
    await userEvent.type(input, 'Combien pèse E2E-001 ?{Enter}')
    await vi.waitFor(() => expect(ask).toHaveBeenCalledWith(3, 'Combien pèse E2E-001 ?'))
    expect(create).toHaveBeenCalledWith(1)
  })
})
