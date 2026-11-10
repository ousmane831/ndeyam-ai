import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Scale, TrendingUp } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { Button } from '@/components/ui/Button'
import { Alert, Card, EmptyState, AnimalTag } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { PageHeader, td, th } from '@/components/ui/Layout'
import { Spinner } from '@/components/ui/Spinner'
import { METHOD_OPTIONS } from '@/features/animals/constants'
import { useFarm } from '@/hooks/useFarm'
import { ApiError } from '@/services/api'
import { isOnline } from '@/features/offline/connectivity'
import { isNetworkError, outbox } from '@/features/offline/outbox'
import { loadPack } from '@/features/offline/pack'
import { animalService, groupService, weighingService } from '@/services/animals'
import type { Animal, WeighingMethod } from '@/types/animal'
import { formatDate, formatNumber, todayIso } from '@/utils/format'

/** Séance de pesée : tous les animaux présents d'un lot, une même date, enregistrement en une fois. */
function WeighingSession({ groupId, farmId }: { groupId: number | null; farmId: number | null }) {
  const queryClient = useQueryClient()
  const animals = useQuery({
    queryKey: ['animals', { group: groupId, farm: farmId, session: true }],
    queryFn: () => animalService.list({ group: groupId ? String(groupId) : undefined, farm: farmId, page: 1 }),
  })
  const [date, setDate] = useState(todayIso())
  const [method, setMethod] = useState<WeighingMethod>('SCALE')
  const [weights, setWeights] = useState<Record<number, string>>({})
  const [errors, setErrors] = useState<Record<number, string>>({})
  const [message, setMessage] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  // Sans réseau et sans liste en mémoire : les animaux présents du paquet hors ligne (téléchargé à la connexion).
  const offlineList = useMemo(() => {
    if (animals.data || farmId === null) return null
    const pack = loadPack(farmId)
    return pack ? (pack.animals.filter((a) => !groupId || a.group === groupId) as unknown as Animal[]) : null
  }, [animals.data, farmId, groupId])
  const list = animals.data?.results ?? offlineList ?? []
  const filled = list.filter((a) => (weights[a.id] ?? '').trim() !== '')

  const submit = async () => {
    setMessage(null)
    const localErrors: Record<number, string> = {}
    for (const a of filled) {
      const n = Number(weights[a.id].replace(',', '.'))
      if (!(n > 0)) localErrors[a.id] = 'Poids positif attendu.'
    }
    if (date > todayIso()) {
      setMessage({ tone: 'error', text: 'La date ne peut pas être dans le futur.' })
      return
    }
    setErrors(localErrors)
    if (Object.keys(localErrors).length || filled.length === 0) {
      if (filled.length === 0) setMessage({ tone: 'error', text: 'Saisissez au moins un poids.' })
      return
    }
    setBusy(true)
    const payload = {
      weighed_on: date,
      method,
      entries: filled.map((a) => ({ animal: a.id, weight_kg: weights[a.id].replace(',', '.') })),
    }
    // Sans réseau, la séance est gardée sur l'appareil et envoyée au retour de la connexion.
    const keepForLater = () => {
      outbox.add({ kind: 'weighing-session', payload, label: `Séance de pesée du ${formatDate(date)} (${filled.length} animal(aux))` })
      setWeights({})
      setMessage({ tone: 'success', text: `Hors ligne : ${filled.length} pesée(s) gardée(s) sur cet appareil, envoyée(s) automatiquement au retour du réseau.` })
    }
    if (!isOnline()) {
      keepForLater()
      setBusy(false)
      return
    }
    try {
      const created = await weighingService.bulk(payload)
      setWeights({})
      setMessage({ tone: 'success', text: `${created.length} pesée(s) enregistrée(s).` })
      for (const key of ['animals', 'growth', 'weighings', 'group-growth', 'alerts', 'dashboard']) {
        queryClient.invalidateQueries({ queryKey: [key] })
      }
    } catch (e) {
      if (isNetworkError(e)) {
        keepForLater()
      } else if (e instanceof ApiError && Object.keys(e.fieldErrors).length) {
        // Erreurs indexées par ligne de la séance (0, 1, …).
        const serverErrors: Record<number, string> = {}
        for (const [index, messages] of Object.entries(e.fieldErrors)) {
          const animal = filled[Number(index)]
          if (animal) serverErrors[animal.id] = messages.join(' ')
        }
        setErrors(serverErrors)
        setMessage({ tone: 'error', text: e.message })
      } else {
        setMessage({ tone: 'error', text: e instanceof Error ? e.message : 'Enregistrement impossible.' })
      }
    } finally {
      setBusy(false)
    }
  }

  if (animals.isPending && !offlineList) return <Spinner />
  if (animals.isError && !offlineList) return <Alert tone="error">{animals.error.message}</Alert>
  if (list.length === 0) return <EmptyState title="Aucun animal présent dans ce lot" />

  return (
    <div className="space-y-4">
      {message && <Alert tone={message.tone}>{message.text}</Alert>}
      <div className="grid gap-4 sm:grid-cols-3">
        <TextField label="Date de la séance" type="date" max={todayIso()} value={date} onChange={(e) => setDate(e.target.value)} />
        <SelectField label="Méthode" options={METHOD_OPTIONS} value={method} onChange={(e) => setMethod(e.target.value as WeighingMethod)} />
      </div>
      <div className="-mx-5 overflow-x-auto">
        <table className="w-full">
          <thead className="border-y border-slate-200 bg-slate-50">
            <tr>
              <th className={th}>Animal</th>
              <th className={th}>Dernier poids</th>
              <th className={th}>Nouveau poids (kg)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {list.map((a) => (
              <tr key={a.id}>
                <td className={td}>
                  <AnimalTag>{a.tag_number}</AnimalTag> {a.name && <span className="ml-1 text-slate-500">{a.name}</span>}
                </td>
                <td className={td}>{a.last_weight ? `${formatNumber(a.last_weight.weight_kg)} kg (${formatDate(a.last_weight.weighed_on)})` : '—'}</td>
                <td className={td}>
                  <input
                    inputMode="decimal"
                    aria-label={`Poids de ${a.tag_number}`}
                    value={weights[a.id] ?? ''}
                    onChange={(e) => setWeights((w) => ({ ...w, [a.id]: e.target.value }))}
                    className={`w-28 rounded-lg border px-2 py-1.5 text-sm ${errors[a.id] ? 'border-red-400' : 'border-slate-300'}`}
                  />
                  {errors[a.id] && <p className="mt-1 text-xs text-red-600">{errors[a.id]}</p>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(animals.data?.count ?? 0) > list.length && (
        <Alert tone="info">Seuls les {list.length} premiers animaux sont affichés : sélectionnez un lot pour une séance plus ciblée.</Alert>
      )}
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-slate-500">{filled.length} poids saisi(s). Les animaux laissés vides ne sont pas pesés.</p>
        <Button onClick={submit} loading={busy} icon={<Scale className="size-4" />}>
          Enregistrer la séance
        </Button>
      </div>
    </div>
  )
}

function GroupGrowthTable({ groupId }: { groupId: number }) {
  const growth = useQuery({ queryKey: ['group-growth', groupId], queryFn: () => groupService.growth(groupId) })
  if (growth.isPending) return <Spinner />
  if (growth.isError) return <Alert tone="error">{growth.error.message}</Alert>
  const g = growth.data
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg bg-slate-50 p-4">
          <p className="text-xs font-medium text-slate-500 uppercase">GMD moyen du lot</p>
          <p className="mt-1 text-xl font-semibold">{g.mean_adg_g_per_day ? `${formatNumber(g.mean_adg_g_per_day)} g/j` : '—'}</p>
          <p className="mt-1 text-xs text-slate-500">
            Sur {g.animals_with_adg} animal(aux) mesurable(s) sur {g.animals_count}.
          </p>
        </div>
        <p className="text-xs text-slate-500 sm:col-span-2 sm:self-center">{g.note}</p>
      </div>
      <div className="-mx-5 overflow-x-auto">
        <table className="w-full">
          <thead className="border-y border-slate-200 bg-slate-50">
            <tr>
              <th className={th}>Animal</th>
              <th className={th}>Dernier poids</th>
              <th className={th}>Mesures</th>
              <th className={th}>GMD sur la période</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {g.animals.map((a) => (
              <tr key={a.animal_id}>
                <td className={td}>
                  <Link to={`/animaux/${a.animal_id}`} className="inline-block align-middle hover:opacity-80">
                    <AnimalTag>{a.tag_number}</AnimalTag>
                  </Link>
                </td>
                <td className={td}>{a.last_weight_kg ? `${formatNumber(a.last_weight_kg)} kg (${formatDate(a.last_weighed_on)})` : '—'}</td>
                <td className={td}>{a.measurements}</td>
                <td className={td}>{a.adg_g_per_day ? `${formatNumber(a.adg_g_per_day)} g/j` : 'Non calculable'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function GrowthPage() {
  const [params, setParams] = useSearchParams()
  const { selectedFarmId, writableFarms, canWrite } = useFarm()
  const groups = useQuery({ queryKey: ['groups', selectedFarmId], queryFn: () => groupService.list(selectedFarmId) })
  const groupId = params.get('lot') ? Number(params.get('lot')) : null
  const group = useMemo(() => groups.data?.results.find((g) => g.id === groupId), [groups.data, groupId])
  const sessionAllowed = group ? canWrite(group.farm) : writableFarms.length > 0 && selectedFarmId !== null && canWrite(selectedFarmId)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Suivi de croissance"
        description="Pesées par séance et gain moyen quotidien (GMD) des lots. La courbe individuelle se trouve dans la fiche de chaque animal."
      />
      <Card>
        <SelectField
          label="Lot"
          value={groupId ? String(groupId) : ''}
          onChange={(e) => setParams(e.target.value ? { lot: e.target.value } : {})}
          options={[
            { value: '', label: selectedFarmId ? "Tous les animaux de l'exploitation" : 'Choisir un lot…' },
            ...(groups.data?.results ?? []).map((g) => ({ value: String(g.id), label: `${g.name} (${g.animals_count})` })),
          ]}
        />
      </Card>

      {group && (
        <Card title={`GMD du lot « ${group.name} »`}>
          <GroupGrowthTable groupId={group.id} />
        </Card>
      )}

      <Card title="Séance de pesée">
        {sessionAllowed && (groupId || selectedFarmId) ? (
          <WeighingSession groupId={groupId} farmId={group ? group.farm : selectedFarmId} />
        ) : (
          <EmptyState icon={<TrendingUp className="size-10" />} title="Choisissez un lot pour démarrer une séance de pesée">
            {writableFarms.length === 0
              ? 'Votre accès est en lecture seule.'
              : 'Sélectionnez un lot ci-dessus (ou une exploitation dans le menu du haut) pour saisir les poids de plusieurs animaux à la même date.'}
          </EmptyState>
        )}
      </Card>
      {!groupId && writableFarms.length > 0 && (
        <p className="text-sm text-slate-500">
          Astuce : créez des lots dans <Link to="/troupeaux" className="text-brand-700 hover:underline">Mes troupeaux</Link> pour peser par groupe.
        </p>
      )}
      {groupId && !group && groups.isSuccess && <Alert tone="warning">Ce lot est introuvable dans l'exploitation sélectionnée.</Alert>}
    </div>
  )
}
