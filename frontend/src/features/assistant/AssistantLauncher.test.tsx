import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { assistantService } from '@/services/assistant'
import { breeder, fakeAuth, renderWithProviders } from '@/test/utils'
import { AssistantLauncher } from './AssistantLauncher'

const auth = () => fakeAuth({ status: 'authenticated', user: breeder })
const configured = () =>
  vi.spyOn(assistantService, 'status').mockResolvedValue({ configured: true, provider: 'anthropic', model: 'claude-opus-5-5', message: '' })

describe('AssistantLauncher', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(assistantService, 'status').mockResolvedValue({
      configured: false, provider: null, model: null, message: "L'assistant IA n'est pas configuré (LLM_PROVIDER=none).",
    })
  })

  it("sans assistant activé, le bouton bélier ouvre un guide et un glossaire, sans jargon technique", async () => {
    renderWithProviders(<AssistantLauncher />, { auth: auth() })
    const launcher = screen.getByRole('button', { name: "Ouvrir l'assistant Ndeyam AI" })
    expect(launcher).toHaveAttribute('aria-expanded', 'false')

    await userEvent.click(launcher)
    expect(await screen.findByRole('dialog', { name: 'Guide Ndeyam AI' })).toBeInTheDocument()
    // Le focus reste dans le panneau (sur « Fermer ») pour la navigation au clavier.
    await vi.waitFor(() => expect(screen.getByRole('button', { name: "Fermer l'assistant" })).toHaveFocus())
    expect(screen.getByText('Peser vos animaux')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Séance de pesée/ })).toHaveAttribute('href', '/suivi-croissance')
    expect(screen.queryByText(/backend\/\.env/)).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Votre question')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: 'Glossaire' }))
    expect(screen.getByText('MS (matière sèche)')).toBeInTheDocument()

    await userEvent.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it("l'indication technique d'activation n'est montrée qu'aux administrateurs", async () => {
    renderWithProviders(<AssistantLauncher />, { auth: fakeAuth({ status: 'authenticated', user: { ...breeder, is_platform_admin: true } }) })
    await userEvent.click(screen.getByRole('button', { name: "Ouvrir l'assistant Ndeyam AI" }))
    expect(await screen.findByText('LLM_PROVIDER')).toBeInTheDocument()
  })

  it("assistant activé : discussion, vue plein écran, et masqué sur la page de l'assistant", async () => {
    configured()
    const { unmount } = renderWithProviders(<AssistantLauncher />, { auth: auth() })
    await userEvent.click(screen.getByRole('button', { name: "Ouvrir l'assistant Ndeyam AI" }))
    expect(await screen.findByRole('dialog', { name: 'Assistant Ndeyam AI' })).toBeInTheDocument()
    expect(screen.getByText(/ne pose aucun diagnostic vétérinaire/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /plein écran/ })).toHaveAttribute('href', '/assistant')
    unmount()

    renderWithProviders(<AssistantLauncher />, { auth: auth(), route: '/assistant' })
    expect(screen.queryByRole('button', { name: "Ouvrir l'assistant Ndeyam AI" })).not.toBeInTheDocument()
  })

  it('envoie une question depuis le panneau', async () => {
    configured()
    const create = vi.spyOn(assistantService, 'create').mockResolvedValue({
      id: 3, title: '', farm: 1, is_archived: false, messages_count: 0, created_at: '', updated_at: '',
    })
    const ask = vi.spyOn(assistantService, 'ask').mockResolvedValue([])
    vi.spyOn(assistantService, 'get').mockResolvedValue({
      id: 3, title: 'q', farm: 1, is_archived: false, messages_count: 0, created_at: '', updated_at: '', messages: [],
    })
    renderWithProviders(<AssistantLauncher />, { auth: auth() })
    await userEvent.click(screen.getByRole('button', { name: "Ouvrir l'assistant Ndeyam AI" }))
    const input = await screen.findByLabelText('Votre question')
    await vi.waitFor(() => expect(input).toBeEnabled())
    await vi.waitFor(() => expect(input).toHaveFocus())
    await userEvent.type(input, 'Combien pèse E2E-001 ?{Enter}')
    await vi.waitFor(() => expect(ask).toHaveBeenCalledWith(3, 'Combien pèse E2E-001 ?'))
    expect(create).toHaveBeenCalledWith(1)
  })
})
