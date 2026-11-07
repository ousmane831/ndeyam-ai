import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MessageSquarePlus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, Card, EmptyState } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { ConfirmDialog } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { animalService } from '@/services/animals'
import type { Observation } from '@/types/animal'
import { formatDate, todayIso } from '@/utils/format'

const KINDS = [
  { value: 'GENERAL', label: 'Générale' },
  { value: 'FEEDING', label: 'Alimentation' },
  { value: 'BEHAVIOR', label: 'Comportement' },
  { value: 'HEALTH', label: 'État de santé observé (non diagnostique)' },
  { value: 'REPRODUCTION', label: 'Reproduction' },
  { value: 'OTHER', label: 'Autre' },
]

export function ObservationsTab({ animalId, canWrite }: { animalId: number; canWrite: boolean }) {
  const queryClient = useQueryClient()
  const key = ['observations', animalId]
  const observations = useQuery({ queryKey: key, queryFn: () => animalService.observations(animalId) })
  const [text, setText] = useState('')
  const [kind, setKind] = useState('GENERAL')
  const [date, setDate] = useState(todayIso())
  const [error, setError] = useState<string | null>(null)
  const [toDelete, setToDelete] = useState<Observation | null>(null)

  const add = useMutation({
    mutationFn: () => animalService.addObservation(animalId, { text: text.trim(), kind, observed_on: date }),
    onSuccess: () => {
      setText('')
      queryClient.invalidateQueries({ queryKey: key })
    },
    onError: (e: Error) => setError(e.message),
  })
  const removal = useMutation({
    mutationFn: (o: Observation) => animalService.removeObservation(animalId, o.id),
    onSuccess: () => {
      setToDelete(null)
      queryClient.invalidateQueries({ queryKey: key })
    },
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!text.trim()) {
      setError("Saisissez le texte de l'observation.")
      return
    }
    if (date > todayIso()) {
      setError('La date ne peut pas être dans le futur.')
      return
    }
    add.mutate()
  }

  return (
    <div className="space-y-6">
      {canWrite && (
        <Card title="Nouvelle observation">
          <form onSubmit={submit} noValidate className="space-y-4">
            {error && <Alert tone="error">{error}</Alert>}
            <div className="grid gap-4 sm:grid-cols-[180px_1fr]">
              <TextField label="Date" type="date" max={todayIso()} value={date} onChange={(e) => setDate(e.target.value)} />
              <SelectField label="Type" options={KINDS} value={kind} onChange={(e) => setKind(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="obs-text" className="block text-sm font-medium text-slate-700">
                Observation <span className="text-red-600">*</span>
              </label>
              <textarea
                id="obs-text"
                rows={3}
                value={text}
                onChange={(e) => setText(e.target.value)}
                className="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              {kind === 'HEALTH' && (
                <p className="text-xs text-slate-500">
                  Notez ce que vous observez. NDEYAM AI ne pose aucun diagnostic : en cas de doute, consultez un vétérinaire.
                </p>
              )}
            </div>
            <div className="flex justify-end">
              <Button type="submit" loading={add.isPending} icon={<MessageSquarePlus className="size-4" />}>
                Ajouter
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card title="Observations">
        {observations.isPending ? (
          <Spinner />
        ) : observations.isError ? (
          <Alert tone="error">{observations.error.message}</Alert>
        ) : observations.data.length === 0 ? (
          <EmptyState title="Aucune observation" />
        ) : (
          <ul className="divide-y divide-slate-100">
            {observations.data.map((o) => (
              <li key={o.id} className="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span>{formatDate(o.observed_on)}</span>
                    <Badge>{o.kind_label}</Badge>
                    {o.author_email && <span>{o.author_email}</span>}
                  </div>
                  <p className="mt-1 text-sm whitespace-pre-line text-slate-800">{o.text}</p>
                </div>
                {canWrite && (
                  <button
                    type="button"
                    onClick={() => setToDelete(o)}
                    className="rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                    aria-label="Supprimer l'observation"
                  >
                    <Trash2 className="size-4" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <ConfirmDialog
        open={toDelete !== null}
        title="Supprimer cette observation ?"
        message="Cette action est définitive."
        confirmLabel="Supprimer"
        danger
        loading={removal.isPending}
        onConfirm={() => toDelete && removal.mutate(toDelete)}
        onCancel={() => setToDelete(null)}
      />
    </div>
  )
}
