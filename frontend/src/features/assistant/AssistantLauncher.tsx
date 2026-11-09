import clsx from 'clsx'
import { Maximize2, MessageSquarePlus, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router'
import { Logo } from '@/components/ui/Logo'
import { useAuth } from '@/hooks/useAuth'
import { ChatThread } from './AssistantChat'
import { GuidePanel } from './GuidePanel'
import { useAssistantChat } from './useAssistantChat'

/**
 * Assistant flottant (bas droite) : bouton à tête de bélier, panneau de discussion.
 * Le composant reste monté : la conversation en cours survit à la fermeture du panneau
 * et à la navigation entre les pages.
 */
export function AssistantLauncher() {
  const [open, setOpen] = useState(false)
  const { user } = useAuth()
  const chat = useAssistantChat()
  const { pathname } = useLocation()
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const launcherRef = useRef<HTMLButtonElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const statusKnown = !chat.status.isLoading
  // Assistant non activé : le bouton bélier ouvre le guide et le glossaire, jamais un message technique.
  const guideMode = statusKnown && !chat.configured

  // À l'ouverture : focus dans la zone de saisie si l'assistant répond, sinon sur « Fermer »
  // (un champ désactivé ne peut pas recevoir le focus ; il ne doit jamais rester hors du panneau).
  useEffect(() => {
    if (!open || !statusKnown) return
    if (chat.configured && inputRef.current) inputRef.current.focus()
    else closeRef.current?.focus()
  }, [open, statusKnown, chat.configured])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        launcherRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  // La vue plein écran a déjà sa propre zone de discussion.
  if (pathname.startsWith('/assistant')) return null

  return (
    <>
      {open && (
        <section
          id="assistant-panel"
          role="dialog"
          aria-label={guideMode ? 'Guide Ndeyam AI' : 'Assistant Ndeyam AI'}
          className={clsx(
            'fixed z-50 flex flex-col overflow-hidden bg-white',
            // Téléphone : plein écran ; ordinateur et tablette : panneau ancré au-dessus du bouton.
            'inset-0 pt-[env(safe-area-inset-top)] pb-[env(safe-area-inset-bottom)]',
            'sm:inset-auto sm:right-6 sm:bottom-24 sm:h-[min(640px,calc(100vh-8rem))] sm:w-[400px] sm:rounded-lg sm:pt-0 sm:pb-0 sm:shadow-[0_18px_50px_-12px_rgb(20_29_58/0.35)] sm:ring-1 sm:ring-slate-200',
          )}
        >
          <header className="bg-brand-900 text-white">
            <div className="flex items-center gap-3 px-4 py-3">
              <Logo className="size-9 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="font-display text-[15px] leading-tight font-bold">{guideMode ? 'Guide Ndeyam AI' : 'Assistant Ndeyam AI'}</p>
                <p className="truncate text-xs text-brand-200">
                  {chat.status.isLoading ? 'Vérification…' : guideMode ? 'Les gestes essentiels et le vocabulaire' : 'Répond à partir de vos données'}
                </p>
              </div>
              {!guideMode && (
                <>
                  <button type="button" onClick={() => chat.open(null)} className="rounded-md p-2.5 text-brand-200 hover:bg-white/10 hover:text-white"
                    aria-label="Nouvelle conversation" title="Nouvelle conversation">
                    <MessageSquarePlus className="size-[18px]" />
                  </button>
                  <Link to="/assistant" onClick={() => setOpen(false)} className="rounded-md p-2.5 text-brand-200 hover:bg-white/10 hover:text-white"
                    aria-label="Ouvrir en plein écran (historique des conversations)" title="Plein écran et historique">
                    <Maximize2 className="size-[18px]" />
                  </Link>
                </>
              )}
              <button ref={closeRef} type="button" onClick={() => setOpen(false)} className="rounded-md p-2.5 text-brand-200 hover:bg-white/10 hover:text-white"
                aria-label="Fermer l'assistant">
                <X className="size-5" />
              </button>
            </div>
          </header>
          <div className="h-[3px] bg-mil-400" aria-hidden />

          {chat.status.isLoading ? null : guideMode ? (
            <GuidePanel onNavigate={() => setOpen(false)} adminNote={Boolean(user?.is_platform_admin)} />
          ) : (
            <>
              <p className="border-b border-slate-100 px-4 py-2 text-[13px] leading-snug text-slate-600">
                Explique vos données et les résultats du moteur. Ne calcule aucune ration et ne pose aucun diagnostic vétérinaire.
              </p>
              <div className="flex min-h-0 flex-1 flex-col">
                <ChatThread chat={chat} compact inputRef={inputRef} />
              </div>
            </>
          )}
        </section>
      )}

      <button
        ref={launcherRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="assistant-panel"
        aria-label={open ? "Fermer l'assistant Ndeyam AI" : "Ouvrir l'assistant Ndeyam AI"}
        title={guideMode ? 'Guide Ndeyam AI' : 'Assistant Ndeyam AI'}
        className={clsx(
          'group fixed z-50 rounded-[14px] transition-transform focus-visible:outline-offset-4 motion-safe:hover:-translate-y-0.5',
          'right-[max(1.25rem,env(safe-area-inset-right))] bottom-[max(1.25rem,env(safe-area-inset-bottom))] sm:right-6 sm:bottom-6',
          'shadow-[0_10px_28px_-6px_rgb(20_29_58/0.45)]',
          open && 'max-sm:hidden',
        )}
      >
        {open ? (
          <span className="flex size-14 items-center justify-center rounded-[14px] bg-brand-900 text-white">
            <X className="size-6" />
          </span>
        ) : (
          <Logo className="size-14" />
        )}
        {!open && (
          <span className="pointer-events-none absolute right-full top-1/2 mr-3 hidden -translate-y-1/2 whitespace-nowrap rounded-md bg-brand-900 px-3 py-1.5 text-xs font-semibold text-white opacity-0 transition-opacity group-hover:opacity-100 sm:block">
            {guideMode ? 'Guide Ndeyam AI' : 'Assistant Ndeyam AI'}
          </span>
        )}
      </button>
    </>
  )
}
