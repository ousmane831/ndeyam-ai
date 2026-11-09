import clsx from 'clsx'
import { Calculator, Database, FileText, Send, Sparkles } from 'lucide-react'
import { useEffect, useRef, type ReactNode } from 'react'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Feedback'
import { Logo } from '@/components/ui/Logo'
import { Spinner } from '@/components/ui/Spinner'
import type { AssistantMessage, Provenance, ProvenanceType } from '@/services/assistant'
import { formatDateTime } from '@/utils/format'
import { SUGGESTIONS, type AssistantChatState } from './useAssistantChat'


const PROVENANCE: Record<ProvenanceType, { label: string; icon: ReactNode; className: string }> = {
  database: { label: 'Vos données', icon: <Database className="size-3.5" />, className: 'bg-brand-50 text-brand-800 ring-brand-200' },
  engine: { label: 'Moteur nutritionnel', icon: <Calculator className="size-3.5" />, className: 'bg-acacia-50 text-acacia-800 ring-acacia-200' },
  document: { label: 'Document', icon: <FileText className="size-3.5" />, className: 'bg-mil-50 text-mil-700 ring-mil-200' },
  llm: { label: 'Modèle de langage', icon: <Sparkles className="size-3.5" />, className: 'bg-slate-100 text-slate-700 ring-slate-200' },
}

function ProvenanceChips({ items }: { items: Provenance[] }) {
  if (!items.length) return null
  return (
    <div className="mt-3 border-t border-slate-100 pt-2">
      <p className="mb-1.5 text-xs font-medium text-slate-500">Origine des informations</p>
      <ul className="flex flex-wrap gap-1.5">
        {items.map((p) => {
          const meta = PROVENANCE[p.type] ?? PROVENANCE.llm
          return (
            <li key={`${p.type}-${p.label}`} className={clsx('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ring-1', meta.className)}
              title={meta.label}>
              {meta.icon}
              <span><span className="font-medium">{meta.label} :</span> {p.label}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function MessageBubble({ message }: { message: AssistantMessage }) {
  const mine = message.role === 'USER'
  const failed = !mine && message.error_code
  return (
    <div className={clsx('flex', mine ? 'justify-end' : 'justify-start')}>
      <div className={clsx('max-w-[88%] rounded-2xl px-4 py-3 text-sm',
        mine ? 'rounded-br-sm bg-brand-800 text-white' : failed ? 'rounded-bl-sm bg-mil-50 text-mil-700 ring-1 ring-mil-200' : 'rounded-bl-sm bg-white text-slate-800 ring-1 ring-slate-200')}>
        {!mine && <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-slate-500"><Logo className="size-4" /> Assistant Ndeyam AI</p>}
        <div className="whitespace-pre-wrap">{message.content}</div>
        {!mine && <ProvenanceChips items={message.provenance} />}
        <p className={clsx('mt-1 text-right text-xs', mine ? 'text-brand-200' : 'text-slate-500')}>{formatDateTime(message.created_at)}</p>
      </div>
    </div>
  )
}


/** Fil de discussion + zone de saisie. `compact` : version panneau flottant. */
export function ChatThread({ chat, compact = false, inputRef }: { chat: AssistantChatState; compact?: boolean; inputRef?: React.Ref<HTMLTextAreaElement> }) {
  const endRef = useRef<HTMLDivElement>(null)
  const { messages, pending, configured, detail, activeId } = chat

  useEffect(() => {
    // Défiler vers le dernier message seulement s'il y en a : l'accueil vide reste lu depuis le haut.
    if (messages.length === 0 && !pending) return
    endRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
  }, [messages.length, pending])

  return (
    <>
      <div className={clsx('flex-1 space-y-3 overflow-y-auto bg-slate-50', compact ? 'p-3' : 'p-4')}>
        {activeId && detail.isLoading && <Spinner />}
        {messages.length === 0 && !pending && !(activeId && detail.isLoading) && (
          <div className={clsx('text-center', compact ? 'py-3' : 'py-6')}>
            <Logo className="mx-auto size-11" />
            <p className="mt-3 font-display text-base font-semibold text-slate-800">Comment puis-je vous aider ?</p>
            <p className="text-sm text-slate-500">Quelques exemples :</p>
            <div className={clsx('mt-3 flex gap-2', compact ? 'flex-col items-stretch' : 'flex-wrap justify-center')}>
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" disabled={!configured} onClick={() => chat.setDraft(s)}
                  className={clsx('rounded-full bg-white px-3 py-1.5 text-sm text-slate-700 ring-1 ring-slate-200 hover:ring-brand-300 disabled:opacity-50', compact && 'text-left')}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => <MessageBubble key={m.id} message={m} />)}
        {pending && (
          <>
            <div className="flex justify-end"><div className="max-w-[88%] rounded-2xl rounded-br-sm bg-brand-800 px-4 py-3 text-sm whitespace-pre-wrap text-white">{pending}</div></div>
            <div className="flex items-center gap-2 text-sm text-slate-500"><Spinner /> L'assistant consulte vos données…</div>
          </>
        )}
        <div ref={endRef} />
      </div>
      <form onSubmit={chat.submit} className="border-t border-slate-200 bg-white p-3">
        {chat.error && <Alert tone="error" className="mb-2">{chat.error}</Alert>}
        <div className="flex items-end gap-2">
          <label htmlFor={compact ? 'assistant-question-panel' : 'assistant-question'} className="sr-only">Votre question</label>
          <textarea id={compact ? 'assistant-question-panel' : 'assistant-question'} ref={inputRef} rows={2} maxLength={2000} value={chat.draft} disabled={!configured}
            placeholder={configured ? (compact ? 'Votre question…' : 'Votre question… (Entrée pour envoyer, Maj+Entrée pour aller à la ligne)') : 'Assistant non configuré'}
            onChange={(e) => chat.setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); chat.submit() } }}
            className="block flex-1 resize-none rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none disabled:bg-slate-50" />
          <Button type="submit" disabled={!configured || !chat.draft.trim()} loading={chat.isSending} icon={<Send className="size-4" />}
            aria-label="Envoyer">{compact ? null : 'Envoyer'}</Button>
        </div>
        {!compact && chat.status.data?.model && <p className="mt-1.5 text-xs text-slate-500">Modèle : {chat.status.data.model}</p>}
      </form>
    </>
  )
}
