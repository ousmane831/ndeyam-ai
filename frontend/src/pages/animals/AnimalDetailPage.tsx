import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Archive, ArrowLeft, Pencil, RotateCcw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, Card, AnimalTag } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { DefinitionList, PageHeader, Tabs } from '@/components/ui/Layout'
import { ConfirmDialog, Modal } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { AlertList } from '@/features/alerts/AlertList'
import { FeedingHistoryTab, RationsTab } from '@/features/animals/FeedingTabs'
import { ObservationsTab } from '@/features/animals/ObservationsTab'
import { WeighingsTab } from '@/features/animals/WeighingsTab'
import { useFarm } from '@/hooks/useFarm'
import { alertService } from '@/services/alerts'
import { animalService } from '@/services/animals'
import type { Animal } from '@/types/animal'
import { formatAge, formatDate, formatNumber } from '@/utils/format'

type TabId = 'general' | 'weighings' | 'feeding' | 'rations' | 'observations' | 'alerts'

function ArchiveModal({ animal, open, onClose }: { animal: Animal; open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<'SOLD' | 'DEAD' | 'ARCHIVED'>('SOLD')
  const [note, setNote] = useState('')
  const archive = useMutation({
    mutationFn: () => animalService.archive(animal.id, status, note),
    onSuccess: (updated) => {
      queryClient.setQueryData(['animal', animal.id], updated)
      queryClient.invalidateQueries({ queryKey: ['animals'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      onClose()
    },
  })
  return (
    <Modal
      open={open}
      title={`Sortie de ${animal.tag_number}`}
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button onClick={() => archive.mutate()} loading={archive.isPending}>
            Confirmer la sortie
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {archive.isError && <Alert tone="error">{archive.error.message}</Alert>}
        <p className="text-sm text-slate-600">L'animal n'apparaîtra plus parmi les animaux présents ; son historique est conservé.</p>
        <SelectField
          label="Motif"
          value={status}
          onChange={(e) => setStatus(e.target.value as typeof status)}
          options={[
            { value: 'SOLD', label: 'Vendu' },
            { value: 'DEAD', label: 'Mort' },
            { value: 'ARCHIVED', label: 'Archivé (autre motif)' },
          ]}
        />
        <TextField label="Précision (facultatif)" value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
    </Modal>
  )
}

export function AnimalDetailPage() {
  const { id } = useParams()
  const animalId = Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { canWrite } = useFarm()
  const [params] = useSearchParams()
  // Lien direct vers un onglet (ex. un rappel de pesée ouvre « Pesées et croissance »).
  const [tab, setTab] = useState<TabId>(params.get('onglet') === 'pesees' ? 'weighings' : 'general')
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const animal = useQuery({ queryKey: ['animal', animalId], queryFn: () => animalService.get(animalId) })
  const alerts = useQuery({
    queryKey: ['alerts', { animal: animalId }],
    queryFn: () => alertService.list({ animal: animalId }),
    enabled: animal.isSuccess,
  })
  const restore = useMutation({
    mutationFn: () => animalService.restore(animalId),
    onSuccess: (updated) => {
      queryClient.setQueryData(['animal', animalId], updated)
      queryClient.invalidateQueries({ queryKey: ['animals'] })
    },
  })
  const removal = useMutation({
    mutationFn: () => animalService.remove(animalId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['animals'] })
      navigate('/animaux')
    },
  })

  if (animal.isPending) return <Spinner />
  if (animal.isError)
    return (
      <div className="space-y-4">
        <Alert tone="error">{animal.error.message}</Alert>
        <Link to="/animaux" className="text-sm font-medium text-brand-700 hover:underline">
          Retour à la liste
        </Link>
      </div>
    )

  const a = animal.data
  const writable = canWrite(a.farm)
  const openAlerts = alerts.data?.count ?? 0

  return (
    <div className="space-y-6">
      <Link to="/animaux" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft className="size-4" /> Mes animaux
      </Link>
      <PageHeader
        title={<span className="inline-flex flex-wrap items-center gap-3"><AnimalTag size="lg">{a.tag_number}</AnimalTag>{a.name && <span>{a.name}</span>}</span>}
        description={
          <span className="flex flex-wrap items-center gap-2">
            {a.species_name} · {a.sex_label} · {formatAge(a.age_days, a.birth_date_is_estimated)}
            <Badge tone={a.status === 'ACTIVE' ? 'brand' : 'neutral'}>{a.status_label}</Badge>
            {a.is_demo && <Badge tone="demo">DEMO</Badge>}
          </span>
        }
        actions={
          writable && (
            <>
              <Button variant="secondary" icon={<Pencil className="size-4" />} onClick={() => navigate(`/animaux/${a.id}/modifier`)}>
                Modifier
              </Button>
              {a.status === 'ACTIVE' ? (
                <Button variant="secondary" icon={<Archive className="size-4" />} onClick={() => setArchiveOpen(true)}>
                  Sortie
                </Button>
              ) : (
                <Button variant="secondary" icon={<RotateCcw className="size-4" />} loading={restore.isPending} onClick={() => restore.mutate()}>
                  Remettre présent
                </Button>
              )}
              <Button variant="ghost" icon={<Trash2 className="size-4" />} onClick={() => setDeleteOpen(true)}>
                Supprimer
              </Button>
            </>
          )
        }
      />
      {!writable && <Alert tone="info">Accès en lecture seule à cette exploitation.</Alert>}

      <Tabs<TabId>
        active={tab}
        onChange={setTab}
        tabs={[
          { id: 'general', label: 'Informations générales' },
          { id: 'weighings', label: 'Pesées et croissance' },
          { id: 'feeding', label: 'Historique alimentaire' },
          { id: 'rations', label: 'Rations' },
          { id: 'observations', label: 'Observations' },
          { id: 'alerts', label: 'Suivi et alertes', count: openAlerts },
        ]}
      />

      {tab === 'general' && (
        <Card>
          <DefinitionList
            items={[
              { label: 'Numéro / boucle', value: a.tag_number },
              { label: 'Nom', value: a.name || '—' },
              { label: 'Espèce', value: a.species_name },
              { label: 'Race', value: a.breed_name ?? 'Non renseignée' },
              { label: 'Sexe', value: a.sex_label },
              {
                label: 'Date de naissance',
                value: a.birth_date ? `${formatDate(a.birth_date)}${a.birth_date_is_estimated ? ' (estimée)' : ''}` : 'Inconnue',
              },
              { label: 'Poids initial', value: a.initial_weight_kg ? `${formatNumber(a.initial_weight_kg, 2)} kg` : 'Non renseigné' },
              {
                label: 'Dernier poids',
                value: a.last_weight ? `${formatNumber(a.last_weight.weight_kg, 2)} kg le ${formatDate(a.last_weight.weighed_on)}` : 'Aucune pesée',
              },
              { label: 'Catégorie', value: a.category_name ?? 'Non renseignée' },
              { label: 'Stade physiologique', value: a.physiological_stage_name ?? 'Non renseigné' },
              { label: 'Lot', value: a.group_name ?? 'Aucun' },
              { label: "Date d'enregistrement", value: formatDate(a.registered_on) },
              { label: 'Observations', value: a.observations || '—' },
            ]}
          />
          <details className="mt-5 border-t border-slate-100 pt-4 text-sm text-slate-600">
            <summary className="cursor-pointer font-medium text-slate-700">Détails techniques</summary>
            <p className="mt-2">Identifiant interne (synchronisation, exports) : <span className="font-mono text-xs">{a.uuid}</span></p>
          </details>
        </Card>
      )}
      {tab === 'weighings' && <WeighingsTab animal={a} canWrite={writable} />}
      {tab === 'feeding' && <FeedingHistoryTab animalId={a.id} />}
      {tab === 'rations' && <RationsTab animalId={a.id} />}
      {tab === 'observations' && <ObservationsTab animalId={a.id} canWrite={writable} />}
      {tab === 'alerts' && (
        <Card title="Alertes et rappels ouverts">
          <p className="mb-4 text-xs text-slate-500">
            Les alertes signalent des écarts par rapport à des réglages de suivi ou à des plages validées. Elles ne constituent pas un
            diagnostic vétérinaire.
          </p>
          {alerts.isPending ? (
            <Spinner />
          ) : alerts.isError ? (
            <Alert tone="error">{alerts.error.message}</Alert>
          ) : (
            <AlertList alerts={alerts.data.results} canAct={() => writable} emptyTitle="Aucune alerte ouverte pour cet animal" />
          )}
        </Card>
      )}

      <ArchiveModal animal={a} open={archiveOpen} onClose={() => setArchiveOpen(false)} />
      <ConfirmDialog
        open={deleteOpen}
        title="Supprimer définitivement cet animal ?"
        message={
          <>
            Toutes ses pesées, observations et distributions seront supprimées. Pour un animal vendu ou mort, préférez la <strong>sortie</strong>,
            qui conserve l'historique.
            {removal.isError && <span className="mt-2 block text-red-600">{removal.error.message}</span>}
          </>
        }
        confirmLabel="Supprimer"
        danger
        loading={removal.isPending}
        onConfirm={() => removal.mutate()}
        onCancel={() => setDeleteOpen(false)}
      />
    </div>
  )
}
