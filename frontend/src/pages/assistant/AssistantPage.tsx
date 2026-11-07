import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { MessageSquarePlus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Alert, Card } from '@/components/ui/Feedback'
import { PageHeader } from '@/components/ui/Layout'
import { ConfirmDialog } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { ChatThread } from '@/features/assistant/AssistantChat'
import { useAssistantChat } from '@/features/assistant/useAssistantChat'
import { assistantService } from '@/services/assistant'
import { formatDateTime } from '@/utils/format'

export function NotConfiguredNotice({ message }: { message?: string }) {
  return (
    <Alert tone="info" title="Assistant non configuré">
      {message ?? "Le statut de l'assistant n'a pas pu être vérifié."} L'administrateur peut l'activer dans le fichier
      <code className="mx-1">backend/.env</code>(LLM_PROVIDER). Tous les autres modules restent utilisables.
    </Alert>
  )
}

/** Vue plein écran de l'assistant (historique des conversations). Le panneau flottant reste l'accès principal. */
export function AssistantPage() {
  const queryClient = useQueryClient()
  const chat = useAssistantChat()
  const [toDelete, setToDelete] = useState<number | null>(null)
  const conversations = useQuery({ queryKey: ['assistant', 'conversations'], queryFn: assistantService.list })

  const remove = useMutation({
    mutationFn: assistantService.remove,
    onSuccess: (_, id) => {
      if (id === chat.activeId) chat.open(null)
      setToDelete(null)
      queryClient.invalidateQueries({ queryKey: ['assistant', 'conversations'] })
    },
  })

  return (
    <div className="space-y-6">
      <PageHeader title="Assistant Ndeyam AI"
        description="Posez vos questions sur vos animaux, vos rations, vos formules et la documentation technique validée." />

      {chat.status.isLoading ? <Spinner /> : !chat.configured ? <NotConfiguredNotice message={chat.status.data?.message} /> : null}

      <Alert tone="warning">
        L'assistant explique vos données et les résultats du moteur nutritionnel : il ne calcule aucune ration lui-même, ne pose
        aucun diagnostic vétérinaire et ne remplace pas l'avis d'un vétérinaire ou d'un nutritionniste.
      </Alert>

      <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
        <Card title="Conversations" actions={
          <Button size="sm" variant="secondary" icon={<MessageSquarePlus className="size-4" />} onClick={() => chat.open(null)}>Nouvelle</Button>}>
          {conversations.isLoading ? <Spinner /> : (conversations.data?.results.length ?? 0) === 0 ? (
            <p className="text-sm text-slate-500">Aucune conversation.</p>
          ) : (
            <ul className="-mx-2 space-y-1">
              {conversations.data!.results.map((c) => (
                <li key={c.id} className={clsx('group flex items-center gap-1 rounded-md', c.id === chat.activeId ? 'bg-brand-50' : 'hover:bg-slate-50')}>
                  <button type="button" className="min-w-0 flex-1 px-2 py-2 text-left" onClick={() => chat.open(c.id)} aria-current={c.id === chat.activeId || undefined}>
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

        <section aria-label="Conversation" className="flex min-h-[28rem] flex-col overflow-hidden rounded-md ring-1 ring-slate-200">
          <ChatThread chat={chat} />
        </section>
      </div>

      <ConfirmDialog open={toDelete !== null} title="Supprimer la conversation"
        message="La conversation et tous ses messages seront définitivement supprimés."
        confirmLabel="Supprimer" danger onConfirm={() => toDelete && remove.mutate(toDelete)} onCancel={() => setToDelete(null)} loading={remove.isPending} />
    </div>
  )
}
