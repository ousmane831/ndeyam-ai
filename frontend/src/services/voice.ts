import { api } from './api'

export type VoiceIntent = 'ration' | 'weighing' | 'cost' | 'growth' | 'tasks'
export type SpeechLanguage = 'wolof' | 'pulaar' | 'serere'

export interface VoiceStatus {
  configured: boolean
  /** Langues comprises à l'oral (reconnaissance vocale). */
  speech_languages: SpeechLanguage[]
  /** Langues dans lesquelles la réponse peut être lue à voix haute. */
  voice_languages: SpeechLanguage[]
  intents: { code: VoiceIntent; label: string }[]
}

export interface VoiceSegment {
  text: string
  audio_url: string | null
  error: string | null
}

export interface VoiceAnswer {
  language: SpeechLanguage
  /** Ce que le service vocal a entendu (null pour une question touchée). */
  transcript: string | null
  intent: VoiceIntent | 'unknown'
  intent_label: string
  keywords: string[]
  spoken_text: string
  /** Une phrase courte par information, lues l'une après l'autre. */
  segments: VoiceSegment[]
  audio_error: string | null
  /** Réponse en français, avec les chiffres exacts. */
  text: string
  farm: { id: number; name: string; is_demo: boolean }
  data: Record<string, unknown>
}

// Reconnaissance vocale (~10 s) puis synthèse de chaque phrase : prévoir large.
const SLOW = { timeout: 180_000 }

export const voiceService = {
  status: async () => (await api.get<VoiceStatus>('/voice/status/')).data,
  ask: async (audio: Blob, language: SpeechLanguage, farm?: number | null) => {
    const form = new FormData()
    form.append('audio', audio, 'question.wav')
    form.append('language', language)
    if (farm) form.append('farm', String(farm))
    // Le client envoie du JSON par défaut : sans cet en-tête, le fichier serait perdu.
    return (await api.post<VoiceAnswer>('/voice/ask/', form, { ...SLOW, headers: { 'Content-Type': 'multipart/form-data' } })).data
  },
  answer: async (intent: VoiceIntent, language: SpeechLanguage, farm?: number | null) =>
    (await api.post<VoiceAnswer>('/voice/answer/', { intent, language, ...(farm ? { farm } : {}) }, SLOW)).data,
}
