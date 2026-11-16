import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { encodeWav } from './recorder'
import { voiceService, type VoiceAnswer, type VoiceStatus } from '@/services/voice'
import { breeder, fakeAuth, renderWithProviders } from '@/test/utils'
import { VoiceAssistant } from './VoiceAssistant'

const auth = () => fakeAuth({ status: 'authenticated', user: breeder })
const status = (configured: boolean): VoiceStatus => ({
  configured,
  speech_languages: ['wolof', 'pulaar', 'serere'],
  voice_languages: ['wolof', 'pulaar'],
  intents: [],
})
const answer: VoiceAnswer = {
  language: 'wolof', transcript: null, intent: 'cost', intent_label: "Coût de l'alimentation", keywords: [],
  spoken_text: 'Ci fanweer fan yii weesu, dundal sa jur gi jar na: junni franc.',
  segments: [
    { text: 'Ci fanweer fan yii weesu, dundal sa jur gi jar na:', audio_url: 'https://voix.example/a.wav', error: null },
    { text: 'junni franc.', audio_url: 'https://voix.example/b.wav', error: null },
  ],
  audio_error: null,
  text: "Coût de l'alimentation sur les 30 derniers jours : 1 000 FCFA. (Données de démonstration fictives.)",
  farm: { id: 1, name: 'Ferme de Thiès', is_demo: true },
  data: {},
}

describe('VoiceAssistant', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(window.HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)
  })

  it("explique que l'assistant vocal n'est pas activé et désactive les questions", async () => {
    vi.spyOn(voiceService, 'status').mockResolvedValue(status(false))
    renderWithProviders(<VoiceAssistant />, { auth: auth() })
    expect(await screen.findByText('Assistant vocal non activé')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Ration du jour/ })).toBeDisabled()
  })

  it('répond à une question touchée, phrase par phrase, avec le texte français et la mention DEMO', async () => {
    vi.spyOn(voiceService, 'status').mockResolvedValue(status(true))
    const ask = vi.spyOn(voiceService, 'answer').mockResolvedValue(answer)
    renderWithProviders(<VoiceAssistant />, { auth: auth() })
    await userEvent.click(screen.getByRole('button', { name: 'Pulaar' }))
    const cost = screen.getByRole('button', { name: /Coût de l'alimentation/ })
    await waitFor(() => expect(cost).toBeEnabled())
    await userEvent.click(cost)
    const spoken = await screen.findByRole('list', { name: 'Réponse parlée' })
    expect(within(spoken).getAllByRole('listitem')).toHaveLength(2)
    expect(screen.getByText(/1 000 FCFA/)).toBeInTheDocument()
    expect(screen.getByText('DEMO')).toBeInTheDocument()
    expect(ask).toHaveBeenCalledWith('cost', 'pulaar', 1)
    // La première phrase est lue tout de suite.
    expect(within(spoken).getAllByRole('listitem')[0]).toHaveAttribute('aria-current', 'true')
  })

  it("sérère : pas de question parlée (pas de mots-clés), questions par images lues en wolof", async () => {
    vi.spyOn(voiceService, 'status').mockResolvedValue(status(true))
    const ask = vi.spyOn(voiceService, 'answer').mockResolvedValue(answer)
    renderWithProviders(<VoiceAssistant />, { auth: auth() })
    await userEvent.click(screen.getByRole('button', { name: 'Sérère' }))
    expect(await screen.findByText(/Le sérère n'est pas encore compris à l'oral/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Parler' })).toBeDisabled()
    const tasks = screen.getByRole('button', { name: /À faire aujourd'hui/ })
    await waitFor(() => expect(tasks).toBeEnabled())
    await userEvent.click(tasks)
    await waitFor(() => expect(ask).toHaveBeenCalledWith('tasks', 'wolof', 1))
  })
})

describe('encodeWav', () => {
  it('produit un WAV PCM 16 bits mono 16 kHz', async () => {
    const wav = encodeWav(new Float32Array([0, 0.5, -1, 1]))
    const view = new DataView(await wav.arrayBuffer())
    const text = (o: number) => String.fromCharCode(...new Uint8Array(view.buffer, o, 4))
    expect(text(0)).toBe('RIFF')
    expect(text(8)).toBe('WAVE')
    expect(view.getUint16(22, true)).toBe(1)
    expect(view.getUint32(24, true)).toBe(16000)
    expect(view.getUint32(40, true)).toBe(8)
    expect(view.getInt16(48, true)).toBe(-32768)
  })
})
