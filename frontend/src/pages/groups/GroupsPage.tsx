import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Layers, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, EmptyState } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { PageHeader, td, th } from '@/components/ui/Layout'
import { ConfirmDialog, Modal } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { useFarm } from '@/hooks/useFarm'
import { groupService, nomenclatureService } from '@/services/animals'
import type { AnimalGroup } from '@/types/animal'
import { tk } from '@/i18n'
import { applyServerErrors } from '@/utils/forms'

const schema = z.object({
  farm: z.string().min(1, tk("Choisissez l'exploitation.")),
  name: z.string().trim().min(1, tk('Le nom du lot est obligatoire.')).max(150, tk('150 caractères maximum.')),
  species: z.string(),
  description: z.string(),
  is_active: z.boolean(),
})
type Values = z.infer<typeof schema>

function GroupModal({ group, open, onClose }: { group?: AnimalGroup; open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { writableFarms, defaultWritableFarmId } = useFarm()
  const species = useQuery({ queryKey: ['species'], queryFn: nomenclatureService.species, staleTime: Infinity })
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    values: {
      farm: String(group?.farm ?? defaultWritableFarmId ?? ''),
      name: group?.name ?? '',
      species: group?.species ? String(group.species) : '',
      description: group?.description ?? '',
      is_active: group?.is_active ?? true,
    },
  })

  const onSubmit = handleSubmit(async (v) => {
    setServerError(null)
    const payload = { farm: Number(v.farm), name: v.name, species: v.species ? Number(v.species) : null, description: v.description, is_active: v.is_active }
    try {
      if (group) await groupService.update(group.id, payload)
      else await groupService.create(payload)
      await queryClient.invalidateQueries({ queryKey: ['groups'] })
      onClose()
    } catch (error) {
      setServerError(applyServerErrors(error, setError, ['farm', 'name', 'species', 'description']))
    }
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={group ? t('Modifier le lot « {{name}} »', { name: group.name }) : t('Nouveau lot')}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('Annuler')}
          </Button>
          <Button onClick={onSubmit} loading={isSubmitting}>
            {t('Enregistrer')}
          </Button>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {serverError && <Alert tone="error">{serverError}</Alert>}
        {!group && writableFarms.length > 1 && (
          <SelectField
            label={t('Exploitation')}
            required
            error={errors.farm?.message}
            options={writableFarms.map((f) => ({ value: String(f.id), label: f.name }))}
            {...register('farm')}
          />
        )}
        <TextField label={t('Nom du lot')} required error={errors.name?.message} {...register('name')} />
        <SelectField
          label={t('Espèce (facultatif)')}
          hint={t('Si elle est renseignée, seuls les animaux de cette espèce pourront rejoindre le lot.')}
          options={[{ value: '', label: t('Toutes espèces') }, ...(species.data ?? []).map((s) => ({ value: String(s.id), label: t(s.name) }))]}
          {...register('species')}
        />
        <TextField label={t('Description')} {...register('description')} />
        <label className="inline-flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" className="size-5 accent-brand-700" {...register('is_active')} />
          {t('Lot actif')}
        </label>
      </form>
    </Modal>
  )
}

export function GroupsPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { selectedFarmId, canWrite, writableFarms } = useFarm()
  const groups = useQuery({ queryKey: ['groups', selectedFarmId], queryFn: () => groupService.list(selectedFarmId) })
  const [editing, setEditing] = useState<AnimalGroup | 'new' | null>(null)
  const [toDelete, setToDelete] = useState<AnimalGroup | null>(null)
  const removal = useMutation({
    mutationFn: (g: AnimalGroup) => groupService.remove(g.id),
    onSuccess: () => {
      setToDelete(null)
      queryClient.invalidateQueries({ queryKey: ['groups'] })
      queryClient.invalidateQueries({ queryKey: ['animals'] })
    },
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('Mes troupeaux')}
        description={t('Organisez vos animaux en lots pour les pesées, les rations et le suivi collectif.')}
        actions={
          writableFarms.length > 0 && (
            <Button icon={<Plus className="size-4" />} onClick={() => setEditing('new')}>
              {t('Nouveau lot')}
            </Button>
          )
        }
      />
      <section className="overflow-hidden rounded-md border border-slate-200 bg-white">
        {groups.isPending ? (
          <div className="p-6">
            <Spinner />
          </div>
        ) : groups.isError ? (
          <div className="p-4">
            <Alert tone="error">{groups.error.message}</Alert>
          </div>
        ) : groups.data.results.length === 0 ? (
          <EmptyState icon={<Layers className="size-10" />} title={t('Aucun lot')}>
            {t('Créez un lot (par exemple « Brebis gestantes » ou « Embouche Tabaski ») puis affectez-y vos animaux.')}
          </EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  <th className={th}>{t('Lot')}</th>
                  <th className={th}>{t('Espèce')}</th>
                  <th className={th}>{t('Animaux présents')}</th>
                  <th className={th}>{t('Statut')}</th>
                  <th className={th} />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {groups.data.results.map((g) => (
                  <tr key={g.id} className="hover:bg-slate-50/70">
                    <td className={td}>
                      <p className="font-medium text-slate-800">{g.name}</p>
                      {g.description && <p className="text-xs text-slate-500">{g.description}</p>}
                    </td>
                    <td className={td}>{g.species_name ? t(g.species_name) : t('Toutes')}</td>
                    <td className={td}>
                      <Link to={`/suivi-croissance?lot=${g.id}`} className="text-brand-700 hover:underline">
                        {g.animals_count}
                      </Link>
                    </td>
                    <td className={td}>{g.is_active ? <Badge tone="brand">{t('Actif')}</Badge> : <Badge>{t('Inactif')}</Badge>}</td>
                    <td className={`${td} text-right whitespace-nowrap`}>
                      {canWrite(g.farm) && (
                        <>
                          <button type="button" onClick={() => setEditing(g)} className="rounded-md p-2.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700" aria-label={t('Modifier {{name}}', { name: g.name })}>
                            <Pencil className="size-4" />
                          </button>
                          <button type="button" onClick={() => setToDelete(g)} className="rounded-md p-2.5 text-slate-500 hover:bg-red-50 hover:text-red-600" aria-label={t('Supprimer {{name}}', { name: g.name })}>
                            <Trash2 className="size-4" />
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {editing !== null && <GroupModal open group={editing === 'new' ? undefined : editing} onClose={() => setEditing(null)} />}
      <ConfirmDialog
        open={toDelete !== null}
        title={t('Supprimer le lot « {{name}} » ?', { name: toDelete?.name })}
        message={
          <>
            {t('Les animaux du lot sont conservés et deviennent « sans lot ». Les rations et distributions rattachées au lot seront supprimées.')}
            {removal.isError && <span className="mt-2 block text-red-600">{removal.error.message}</span>}
          </>
        }
        confirmLabel={t('Supprimer')}
        danger
        loading={removal.isPending}
        onConfirm={() => toDelete && removal.mutate(toDelete)}
        onCancel={() => setToDelete(null)}
      />
    </div>
  )
}
