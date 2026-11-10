import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useFarm } from '@/hooks/useFarm'
import { ApiError } from '@/services/api'
import { assistantService } from '@/services/assistant'
import { t, tk } from '@/i18n'

export const SUGGESTIONS = [
  tk('Quel est le poids actuel de mes animaux ?'),
  tk('Pourquoi ma dernière formule a-t-elle été refusée ?'),
  tk('Quelles données manquent pour calculer une formule ?'),
  tk('Combien ont coûté les rations de ce mois-ci ?'),
  tk('Quelles alertes sont ouvertes ?'),
]

/** État et actions d'une conversation avec l'assistant (partagés par le panneau flottant et la page). */
export function useAssistantChat() {
  const queryClient = useQueryClient()
  const { selectedFarmId } = useFarm()
  const [activeId, setActiveId] = useState<number | null>(null)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<string | null>(null)

  const status = useQuery({ queryKey: ['assistant', 'status'], queryFn: assistantService.status })
  const detail = useQuery({
    queryKey: ['assistant', 'conversation', activeId],
    queryFn: () => assistantService.get(activeId!),
    enabled: activeId !== null,
  })

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
      setError(e instanceof ApiError ? e.message : t("La question n'a pas pu être envoyée."))
    },
    onSettled: (id) => {
      setPending(null)
      queryClient.invalidateQueries({ queryKey: ['assistant', 'conversations'] })
      if (id) queryClient.invalidateQueries({ queryKey: ['assistant', 'conversation', id] })
    },
  })

  const configured = status.data?.configured ?? false
  return {
    status,
    detail,
    configured,
    activeId,
    draft,
    error,
    pending,
    isSending: ask.isPending,
    messages: activeId ? (detail.data?.messages ?? []) : [],
    setDraft,
    open: (id: number | null) => {
      setActiveId(id)
      setError(null)
    },
    submit: (e?: FormEvent) => {
      e?.preventDefault()
      const content = draft.trim()
      if (content && !ask.isPending) ask.mutate(content)
    },
  }
}

export type AssistantChatState = ReturnType<typeof useAssistantChat>
