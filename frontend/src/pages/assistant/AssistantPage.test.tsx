import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { assistantService, type AssistantMessage, type ConversationDetail } from '@/services/assistant'
import { breeder, fakeAuth, renderWithProviders } from '@/test/utils'
import { AssistantPage } from './AssistantPage'

const empty = { count: 0, next: null, previous: null, results: [] }
const auth = () => fakeAuth({ status: 'authenticated', user: breeder })

const conversation = (messages: AssistantMessage[]): ConversationDetail => ({
  id: 7, title: 'Poids', farm: null, is_archived: false, messages_count: messages.length,
  created_at: '2026-11-07T10:00:00Z', updated_at: '2026-11-07T10:00:00Z', messages,
})

const msg = (over: Partial<AssistantMessage>): AssistantMessage => ({
  id: 1, role: 'USER', content: '', provenance: [], tool_calls: [], provider: '', model: '', error_code: '',
  latency_ms: null, created_at: '2026-11-07T10:00:00Z', ...over,
})

describe('AssistantPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(assistantService, 'list').mockResolvedValue(empty)
  })

  it("indique clairement que l'assistant n'est pas configuré et désactive la saisie", async () => {
    vi.spyOn(assistantService, 'status').mockResolvedValue({
      configured: false, provider: null, model: null, message: "L'assistant IA n'est pas configuré (LLM_PROVIDER=none).",
    })
    renderWithProviders(<AssistantPage />, { auth: auth() })
    expect(await screen.findByText('Assistant non configuré')).toBeInTheDocument()
    expect(screen.getByLabelText('Votre question')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Envoyer' })).toBeDisabled()
    expect(screen.getByText(/ne pose aucun diagnostic vétérinaire/)).toBeInTheDocument()
  })

  it("envoie une question et affiche la réponse avec l'origine des informations", async () => {
    vi.spyOn(assistantService, 'status').mockResolvedValue({ configured: true, provider: 'anthropic', model: 'claude-opus-5-5', message: '' })
    const create = vi.spyOn(assistantService, 'create').mockResolvedValue({ ...conversation([]) })
    const ask = vi.spyOn(assistantService, 'ask').mockResolvedValue([])
    vi.spyOn(assistantService, 'get').mockResolvedValue(conversation([
      msg({ id: 1, role: 'USER', content: 'Combien pèse SN-001 ?' }),
      msg({ id: 2, role: 'ASSISTANT', content: "D'après vos données, SN-001 pèse 32 kg.", provider: 'anthropic',
        provenance: [{ type: 'database', label: "Pesées de l'animal SN-001" }, { type: 'llm', label: 'Rédaction' }] }),
    ]))
    renderWithProviders(<AssistantPage />, { auth: auth() })
    const input = await screen.findByLabelText('Votre question')
    await waitFor(() => expect(input).toBeEnabled())
    await userEvent.type(input, 'Combien pèse SN-001 ?')
    await userEvent.click(screen.getByRole('button', { name: 'Envoyer' }))
    expect(await screen.findByText("D'après vos données, SN-001 pèse 32 kg.")).toBeInTheDocument()
    expect(screen.getByText("Pesées de l'animal SN-001")).toBeInTheDocument()
    expect(screen.getByText('Modèle : claude-opus-5-5')).toBeInTheDocument()
    expect(create).toHaveBeenCalledWith(1) // exploitation sélectionnée
    expect(ask).toHaveBeenCalledWith(7, 'Combien pèse SN-001 ?')
  })

  it("restaure la question et affiche l'erreur si l'envoi échoue", async () => {
    vi.spyOn(assistantService, 'status').mockResolvedValue({ configured: true, provider: 'ollama', model: 'llama', message: '' })
    vi.spyOn(assistantService, 'create').mockResolvedValue({ ...conversation([]) })
    vi.spyOn(assistantService, 'ask').mockRejectedValue(new Error('réseau'))
    vi.spyOn(assistantService, 'get').mockResolvedValue(conversation([]))
    renderWithProviders(<AssistantPage />, { auth: auth() })
    const input = await screen.findByLabelText('Votre question')
    await waitFor(() => expect(input).toBeEnabled())
    await userEvent.type(input, 'Bonjour{Enter}')
    expect(await screen.findByText("La question n'a pas pu être envoyée.")).toBeInTheDocument()
    expect(input).toHaveValue('Bonjour')
  })
})
