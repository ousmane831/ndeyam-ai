import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { Bot, Calculator, Database, FileText, MessageSquarePlus, Send, Sparkles, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { Button } from '@/components/ui/Button'
import { Alert, Card } from '@/components/ui/Feedback'
import { PageHeader } from '@/components/ui/Layout'
import { ConfirmDialog } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { useFarm } from '@/hooks/useFarm'
import { ApiError } from '@/services/api'
import { assistantService, type AssistantMessage, type Provenance, type ProvenanceType } from '@/services/assistant'
import { formatDateTime } from '@/utils/format'

const SUGGESTIONS = [
  'Quel est le poids actuel de mes animaux ?',
  'Pourquoi ma dernière formule a-t-elle été refusée ?',
  "Quelles données manquent pour calculer une formule ?",
  'Combien ont coûté les rations de ce mois-ci ?',
  'Quelles alertes sont ouvertes ?',
]

const PROVENANCE: Record<ProvenanceType, { label: string; icon: ReactNode; className: string }> = {
  database: { label: 'Vos données', icon: <Database className="size-3.5" />, className: 'bg-sky-50 text-sky-800 ring-sky-200' },
  engine: { label: 'Moteur nutritionnel', icon: <Calculator className="size-3.5" />, className: 'bg-brand-50 text-brand-700 ring-brand-200' },
  document: { label: 'Document', icon: <FileText className="size-3.5" />, className: 'bg-violet-50 text-violet-800 ring-violet-200' },
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
      <div className={clsx('max-w-[85%] rounded-2xl px-4 py-3 text-sm',
        mine ? 'bg-brand-600 text-white' : failed ? 'bg-amber-50 text-amber-900 ring-1 ring-amber-200' : 'bg-white text-slate-800 ring-1 ring-slate-200')}>
        {!mine && <p className="mb-1 flex items-center gap-1 text-xs font-semibold text-slate-500"><Bot className="size-3.5" /> Assistant Ndeyam AI</p>}
        <div className="whitespace-pre-wrap">{message.content}</div>
        {!mine && <ProvenanceChips items={message.provenance} />}
        <p className={clsx('mt-1 text-right text-[11px]', mine ? 'text-brand-100' : 'text-slate-400')}>{formatDateTime(message.created_at)}</p>
      </div>
    </div>
  )
}

export function AssistantPage() {
  const queryClient = useQueryClient()
  const { selectedFarmId } = useFarm()
  const [activeId, setActiveId] = useState<number | null>(null)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<string | null>(null)
  const [toDelete, setToDelete] = useState<number | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  const status = useQuery({ queryKey: ['assistant', 'status'], queryFn: assistantService.status })
  const conversations = useQuery({ queryKey: ['assistant', 'conversations'], queryFn: assistantService.list })
  const detail = useQuery({ queryKey: ['assistant', 'conversation', activeId], queryFn: () => assistantService.get(activeId!), enabled: activeId !== null })

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
  }, [detail.data?.messages.length, pending])

  const ask = useMutation({
    mutationFn: async (content: string) => {
      const id = activeId ?? (await assistantService.create(selectedFarmId)).id
      setActiveId(id)
      try {
        await assistantService.ask(id, content)
      } catch (e) {
        // 503 : assistant non configuré — la réponse explicative est enregistrée et affichée dans la conversation.
        if (!(e instanceof ApiError && e.status === 503)) throw e
      }
      return id
    },
    onMutate: (content) => {
      setError(null)
      setPending(content)
      setDraft('')
    },
    onError: (e, content) => {
      setDraft(content)
      setError(e instanceof ApiError ? e.message : "La question n'a pas pu être envoyée.")
    },
    onSettled: (id) => {
      setPending(null)
      queryClient.invalidateQueries({ queryKey: ['assistant', 'conversations'] })
      if (id) queryClient.invalidateQueries({ queryKey: ['assistant', 'conversation', id] })
    },
  })

  const remove = useMutation({
    mutationFn: assistantService.remove,
    onSuccess: (_, id) => {
      if (id === activeId) setActiveId(null)
      setToDelete(null)
      queryClient.invalidateQueries({ queryKey: ['assistant', 'conversations'] })
    },
  })

  const configured = status.data?.configured ?? false
  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    const content = draft.trim()
    if (content && !ask.isPending) ask.mutate(content)
  }
  const messages = activeId ? (detail.data?.messages ?? []) : []

  return (
    <div className="space-y-6">
      <PageHeader title="Assistant Ndeyam AI"
        description="Posez vos questions sur vos animaux, vos rations, vos formules et la documentation technique validée." />

      {status.isLoading ? <Spinner /> : !configured ? (
        <Alert tone="info" title="Assistant non configuré">
          {status.data?.message ?? "Le statut de l'assistant n'a pas pu être vérifié."} L'administrateur peut l'activer dans le fichier
          <code className="mx-1">backend/.env</code>(LLM_PROVIDER). Tous les autres modules restent utilisables.
        </Alert>
      ) : null}

      <Alert tone="warning">
        L'assistant explique vos données et les résultats du moteur nutritionnel : il ne calcule aucune ration lui-même, ne pose
        aucun diagnostic vétérinaire et ne remplace pas l'avis d'un vétérinaire ou d'un nutritionniste.
      </Alert>

      <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
        <Card title="Conversations" actions={
          <Button size="sm" variant="secondary" icon={<MessageSquarePlus className="size-4" />} onClick={() => { setActiveId(null); setError(null) }}>Nouvelle</Button>}>
          {conversations.isLoading ? <Spinner /> : (conversations.data?.results.length ?? 0) === 0 ? (
            <p className="text-sm text-slate-500">Aucune conversation.</p>
          ) : (
            <ul className="-mx-2 space-y-1">
              {conversations.data!.results.map((c) => (
                <li key={c.id} className={clsx('group flex items-center gap-1 rounded-lg', c.id === activeId ? 'bg-brand-50' : 'hover:bg-slate-50')}>
                  <button type="button" className="min-w-0 flex-1 px-2 py-2 text-left" onClick={() => setActiveId(c.id)} aria-current={c.id === activeId || undefined}>
                    <span className="block truncate text-sm font-medium text-slate-800">{c.title || 'Nouvelle conversation'}</span>
                    <span className="block text-xs text-slate-500">{formatDateTime(c.updated_at)}</span>
                  </button>
                  <button type="button" className="rounded p-1.5 text-slate-400 hover:text-red-600" aria-label={`Supprimer la conversation ${c.title}`}
                    onClick={() => setToDelete(c.id)}>
                    <Trash2 className="size-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <section aria-label="Conversation" className="flex min-h-[28rem] flex-col rounded-xl bg-slate-50 ring-1 ring-slate-200">
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {activeId && detail.isLoading && <Spinner />}
            {messages.length === 0 && !pending && !(activeId && detail.isLoading) && (
              <div className="py-6 text-center">
                <Bot className="mx-auto size-10 text-brand-600" />
                <p className="mt-2 font-medium text-slate-800">Comment puis-je vous aider ?</p>
                <p className="text-sm text-slate-500">Quelques exemples :</p>
                <div className="mt-3 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} type="button" disabled={!configured} onClick={() => setDraft(s)}
                      className="rounded-full bg-white px-3 py-1.5 text-sm text-slate-700 ring-1 ring-slate-200 hover:ring-brand-300 disabled:opacity-50">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m) => <MessageBubble key={m.id} message={m} />)}
            {pending && (
              <>
                <div className="flex justify-end"><div className="max-w-[85%] rounded-2xl bg-brand-600 px-4 py-3 text-sm whitespace-pre-wrap text-white">{pending}</div></div>
                <div className="flex items-center gap-2 text-sm text-slate-500"><Spinner /> L'assistant consulte vos données…</div>
              </>
            )}
            <div ref={endRef} />
          </div>
          <form onSubmit={submit} className="border-t border-slate-200 bg-white p-3">
            {error && <Alert tone="error" className="mb-2">{error}</Alert>}
            <div className="flex items-end gap-2">
              <label htmlFor="assistant-question" className="sr-only">Votre question</label>
              <textarea id="assistant-question" rows={2} maxLength={2000} value={draft} disabled={!configured}
                placeholder={configured ? 'Votre question… (Entrée pour envoyer, Maj+Entrée pour aller à la ligne)' : 'Assistant non configuré'}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
                className="block flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50" />
              <Button type="submit" disabled={!configured || !draft.trim()} loading={ask.isPending} icon={<Send className="size-4" />}>Envoyer</Button>
            </div>
            {status.data?.model && <p className="mt-1.5 text-xs text-slate-400">Modèle : {status.data.model}</p>}
          </form>
        </section>
      </div>

      <ConfirmDialog open={toDelete !== null} title="Supprimer la conversation"
        message="La conversation et tous ses messages seront définitivement supprimés."
        confirmLabel="Supprimer" danger onConfirm={() => toDelete && remove.mutate(toDelete)} onCancel={() => setToDelete(null)} loading={remove.isPending} />
    </div>
  )
}
