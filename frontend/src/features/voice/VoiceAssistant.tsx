import { useMutation, useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { Banknote, ClipboardCheck, Mic, Scale, Square, TrendingUp, Volume2, Wheat } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/Button'
import { Alert, Badge } from '@/components/ui/Feedback'
import { Spinner } from '@/components/ui/Spinner'
import { canRecord, startRecording, type Recording } from './recorder'
import { useFarm } from '@/hooks/useFarm'
import { tk } from '@/i18n'
import { ApiError } from '@/services/api'
import { voiceService, type SpeechLanguage, type VoiceAnswer, type VoiceIntent } from '@/services/voice'

const LANGUAGES: { code: SpeechLanguage; label: string }[] = [
  { code: 'wolof', label: tk('Wolof') },
  { code: 'pulaar', label: tk('Pulaar') },
  { code: 'serere', label: tk('Sérère') },
]

const QUESTIONS: { code: VoiceIntent; label: string; icon: ReactNode }[] = [
  { code: 'ration', label: tk('Ration du jour'), icon: <Wheat className="size-6" /> },
  { code: 'weighing', label: tk('Pesées'), icon: <Scale className="size-6" /> },
  { code: 'growth', label: tk('Croissance'), icon: <TrendingUp className="size-6" /> },
  { code: 'cost', label: tk("Coût de l'alimentation"), icon: <Banknote className="size-6" /> },
  { code: 'tasks', label: tk("À faire aujourd'hui"), icon: <ClipboardCheck className="size-6" /> },
]

const MAX_SECONDS = 60

/** Lit les phrases l'une après l'autre ; renvoie la phrase en cours (-1 : à l'arrêt). */
function useSequentialPlayer() {
  const audio = useRef<HTMLAudioElement | null>(null)
  const [current, setCurrent] = useState(-1)

  const stop = () => {
    audio.current?.pause()
    audio.current = null
    setCurrent(-1)
  }

  const play = (urls: (string | null)[], index = 0) => {
    audio.current?.pause()
    const next = urls.findIndex((url, i) => i >= index && url)
    if (next < 0) {
      audio.current = null
      setCurrent(-1)
      return
    }
    const element = new Audio(urls[next]!)
    audio.current = element
    setCurrent(next)
    element.onended = () => audio.current === element && play(urls, next + 1)
    element.onerror = () => audio.current === element && play(urls, next + 1)
    element.play().catch(() => audio.current === element && setCurrent(-1)) // lecture refusée : bouton « Écouter »
  }

  useEffect(() => () => audio.current?.pause(), [])
  return { current, play, stop }
}

/**
 * Onglet « Parler » du bouton bélier : l'éleveur pose sa question à voix haute (wolof, pulaar, sérère) ou
 * touche une image ; Ndeyam calcule la réponse sur les données de l'exploitation et la lit à voix haute.
 */
export function VoiceAssistant() {
  const { t } = useTranslation()
  const { selectedFarmId } = useFarm()
  const status = useQuery({ queryKey: ['voice', 'status'], queryFn: voiceService.status, staleTime: 5 * 60_000 })
  const [language, setLanguage] = useState<SpeechLanguage>('wolof')
  const [recording, setRecording] = useState<Recording | null>(null)
  const [seconds, setSeconds] = useState(0)
  const [micError, setMicError] = useState<string | null>(null)
  const player = useSequentialPlayer()

  const voiceLanguages = status.data?.voice_languages ?? ['wolof', 'pulaar']
  const answerLanguage: SpeechLanguage = voiceLanguages.includes(language) ? language : 'wolof'
  const configured = status.data?.configured ?? false

  const playAnswer = (answer: VoiceAnswer) => player.play(answer.segments.map((s) => s.audio_url))
  const onAnswer = { onMutate: () => player.stop(), onSuccess: playAnswer }
  const ask = useMutation({ mutationFn: (audio: Blob) => voiceService.ask(audio, language, selectedFarmId), ...onAnswer })
  const touch = useMutation({ mutationFn: (intent: VoiceIntent) => voiceService.answer(intent, answerLanguage, selectedFarmId), ...onAnswer })
  const last = [ask, touch].filter((m) => m.submittedAt).sort((a, b) => b.submittedAt - a.submittedAt)[0]
  const busy = ask.isPending || touch.isPending

  const active = useRef<Recording | null>(null)
  const timer = useRef<number | undefined>(undefined)

  const finish = async () => {
    const rec = active.current
    if (!rec) return
    active.current = null
    window.clearInterval(timer.current)
    setRecording(null)
    try {
      ask.mutate(await rec.stop())
    } catch {
      setMicError(t("L'enregistrement n'a pas pu être lu. Réessayez."))
    }
  }

  // Micro libéré si l'on quitte la page en cours d'enregistrement.
  useEffect(() => () => {
    window.clearInterval(timer.current)
    active.current?.cancel()
  }, [])

  const toggleRecording = async () => {
    setMicError(null)
    if (active.current) return finish()
    try {
      player.stop()
      const rec = await startRecording()
      active.current = rec
      setSeconds(0)
      setRecording(rec)
      // Durée affichée, et arrêt automatique au bout d'une minute.
      let elapsed = 0
      timer.current = window.setInterval(() => {
        elapsed += 1
        setSeconds(elapsed)
        if (elapsed >= MAX_SECONDS) void finish()
      }, 1000)
    } catch {
      setMicError(t("Le micro n'est pas accessible. Autorisez-le dans le navigateur, ou touchez une question ci-dessous."))
    }
  }

  const error = last?.error
  const answer = last?.data

  // La réponse arrive sous les questions : la faire venir à l'écran (le panneau est petit).
  const answerRef = useRef<HTMLElement>(null)
  useEffect(() => {
    if (answer && !busy) answerRef.current?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' })
  }, [answer, busy])

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto bg-slate-50 p-3">
        {status.isLoading ? <Spinner /> : !configured && (
          <Alert tone="info" title={t('Assistant vocal non activé')}>
            {t("Le service de reconnaissance et de synthèse vocale n'est pas configuré sur cette installation (VOICE_SERVICE_URL).")}
          </Alert>
        )}

        <div className="rounded-md bg-white p-3 ring-1 ring-slate-200">
          <div className="flex justify-center gap-2" role="group" aria-label={t('Langue')}>
            {LANGUAGES.map((l) => (
              <button key={l.code} type="button" aria-pressed={language === l.code} onClick={() => setLanguage(l.code)}
                className={clsx('min-h-11 rounded-md px-3 text-sm font-semibold ring-1 ring-inset transition-colors',
                  language === l.code ? 'bg-brand-800 text-white ring-brand-800' : 'bg-white text-brand-800 ring-brand-300 hover:bg-brand-50')}>
                {t(l.label)}
              </button>
            ))}
          </div>
          {answerLanguage !== language && (
            <p className="mt-2 text-center text-[13px] text-slate-600">{t("La réponse sera lue en wolof : la voix sérère n'est pas encore disponible.")}</p>
          )}
          <div className="mt-4 flex flex-col items-center gap-2 text-center">
            <button type="button" onClick={toggleRecording} disabled={!configured || busy || !canRecord()}
              aria-label={recording ? t('Arrêter et envoyer la question') : t('Parler')}
              className={clsx('flex size-20 items-center justify-center rounded-full text-white shadow-md transition-colors disabled:cursor-not-allowed disabled:opacity-50',
                recording ? 'bg-red-700 hover:bg-red-800' : 'bg-brand-800 hover:bg-brand-700')}>
              {recording ? <Square className="size-8" aria-hidden /> : <Mic className="size-9" aria-hidden />}
            </button>
            <p className="text-sm font-medium text-slate-700" aria-live="polite">
              {recording ? t("J'écoute… {{s}} s. Touchez pour envoyer.", { s: seconds })
                : ask.isPending ? t('Ndeyam écoute votre question (environ quinze secondes)…')
                : canRecord() ? t('Touchez le micro et posez votre question.')
                : t("Ce navigateur ne permet pas d'enregistrer : touchez une question ci-dessous.")}
            </p>
            {micError && <Alert tone="warning">{micError}</Alert>}
          </div>
        </div>

        <section aria-labelledby="voice-questions">
          <h2 id="voice-questions" className="mb-2 text-sm font-semibold text-slate-700">{t('Ou touchez une question')}</h2>
          <div className="grid grid-cols-3 gap-2">
            {QUESTIONS.map((q) => (
              <button key={q.code} type="button" onClick={() => touch.mutate(q.code)} disabled={!configured || busy || Boolean(recording)}
                aria-busy={(touch.isPending && touch.variables === q.code) || undefined}
                className="flex min-h-20 flex-col items-center justify-center gap-1.5 rounded-md bg-white p-2 text-center text-xs leading-tight font-semibold text-brand-800 ring-1 ring-brand-200 transition-colors hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-60">
                {touch.isPending && touch.variables === q.code ? <Spinner /> : <span aria-hidden>{q.icon}</span>}
                {t(q.label)}
              </button>
            ))}
          </div>
        </section>

        {error && (
          <Alert tone="error">{error instanceof ApiError ? error.message : t("La réponse n'a pas pu être obtenue. Réessayez.")}</Alert>
        )}

        {answer && !busy && (
          <section ref={answerRef} aria-label={t('Réponse')} className="rounded-md bg-white ring-1 ring-slate-200">
            <div className="flex items-center gap-2 border-b border-slate-100 px-3 py-2">
              <h2 className="min-w-0 flex-1 text-sm font-semibold text-slate-900">
                {t(QUESTIONS.find((q) => q.code === answer.intent)?.label ?? tk('Demande non comprise'))}
              </h2>
              {answer.farm.is_demo && <Badge tone="demo">DEMO</Badge>}
              {answer.segments.some((s) => s.audio_url) && (
                player.current >= 0
                  ? <Button size="sm" variant="secondary" icon={<Square className="size-4" />} onClick={player.stop}>{t('Arrêter')}</Button>
                  : <Button size="sm" variant="secondary" icon={<Volume2 className="size-4" />} onClick={() => playAnswer(answer)}>{t('Écouter')}</Button>
              )}
            </div>
            <div className="space-y-3 p-3">
              {answer.transcript !== null && (
                <p className="text-[13px] text-slate-600">
                  {t('Ndeyam a entendu :')} <q className="italic">{answer.transcript || '…'}</q>
                </p>
              )}
              <ol className="space-y-0.5" aria-label={t('Réponse parlée')} lang={answer.language === 'pulaar' ? 'ff' : 'wo'}>
                {answer.segments.map((s, i) => (
                  <li key={i} aria-current={player.current === i || undefined}
                    className={clsx('rounded-md px-2 py-1 text-[15px]', player.current === i ? 'bg-acacia-50 font-semibold text-acacia-800' : 'text-slate-800')}>
                    {s.text}
                  </li>
                ))}
              </ol>
              <p className="border-t border-slate-200 pt-2 text-[13px] text-slate-700">{answer.text}</p>
              {answer.audio_error && <Alert tone="warning">{answer.audio_error}</Alert>}
            </div>
          </section>
        )}
      </div>
      <p className="border-t border-slate-200 bg-white px-4 py-2.5 text-[13px] leading-snug text-slate-600">
        {t('Réponses calculées à partir de vos données, jamais inventées. Phrases en wolof et pulaar à faire relire par des locuteurs natifs.')}
      </p>
    </div>
  )
}
