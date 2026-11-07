import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, UserPlus, Users } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, Card, EmptyState } from '@/components/ui/Feedback'
import { SelectField, TextField } from '@/components/ui/Field'
import { ConfirmDialog, Modal } from '@/components/ui/Modal'
import { Spinner } from '@/components/ui/Spinner'
import { useAuth } from '@/hooks/useAuth'
import { farmService } from '@/services/farms'
import type { Farm, FarmMember } from '@/types/farm'
import { applyServerErrors } from '@/utils/forms'

const farmSchema = z.object({
  name: z.string().trim().min(1, "Le nom de l'exploitation est obligatoire."),
  region: z.string().trim(),
  locality: z.string().trim(),
  description: z.string().trim(),
})
type FarmValues = z.infer<typeof farmSchema>

const memberSchema = z.object({
  email: z.email('Saisissez une adresse e-mail valide.'),
  role: z.enum(['MANAGER', 'EXPERT']),
})
type MemberValues = z.infer<typeof memberSchema>

function FarmFormModal({ farm, open, onClose }: { farm?: Farm; open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const { reloadUser } = useAuth()
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FarmValues>({
    resolver: zodResolver(farmSchema),
    values: { name: farm?.name ?? '', region: farm?.region ?? '', locality: farm?.locality ?? '', description: farm?.description ?? '' },
  })

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      if (farm) await farmService.update(farm.id, values)
      else await farmService.create(values)
      await queryClient.invalidateQueries({ queryKey: ['farms'] })
      await reloadUser()
      onClose()
    } catch (error) {
      setServerError(applyServerErrors(error, setError, ['name', 'region', 'locality', 'description']))
    }
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={farm ? "Modifier l'exploitation" : 'Nouvelle exploitation'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button onClick={onSubmit} loading={isSubmitting}>
            Enregistrer
          </Button>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {serverError && <Alert tone="error">{serverError}</Alert>}
        <TextField label="Nom" required error={errors.name?.message} {...register('name')} />
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Région" error={errors.region?.message} {...register('region')} />
          <TextField label="Localité" error={errors.locality?.message} {...register('locality')} />
        </div>
        <TextField label="Description" error={errors.description?.message} {...register('description')} />
      </form>
    </Modal>
  )
}

function MembersModal({ farm, open, onClose }: { farm: Farm; open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const canManage = farm.my_role === 'OWNER'
  const membersKey = ['farms', farm.id, 'members']
  const members = useQuery({ queryKey: membersKey, queryFn: () => farmService.members(farm.id), enabled: open })
  const [serverError, setServerError] = useState<string | null>(null)
  const [toRemove, setToRemove] = useState<FarmMember | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<MemberValues>({ resolver: zodResolver(memberSchema), defaultValues: { email: '', role: 'EXPERT' } })

  const removal = useMutation({
    mutationFn: (member: FarmMember) => farmService.removeMember(farm.id, member.id),
    onSuccess: async () => {
      setToRemove(null)
      await queryClient.invalidateQueries({ queryKey: ['farms'] })
    },
  })

  const onAdd = handleSubmit(async (values) => {
    setServerError(null)
    try {
      await farmService.addMember(farm.id, values.email, values.role)
      reset()
      await queryClient.invalidateQueries({ queryKey: ['farms'] })
    } catch (error) {
      setServerError(applyServerErrors(error, setError, ['email', 'role']))
    }
  })

  return (
    <Modal open={open} onClose={onClose} title={`Membres — ${farm.name}`}>
      <div className="space-y-5">
        {members.isPending ? (
          <Spinner />
        ) : members.isError ? (
          <Alert tone="error">{members.error.message}</Alert>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
            {members.data.map((member) => (
              <li key={member.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-800">{member.user_name || member.user_email}</p>
                  <p className="truncate text-xs text-slate-500">{member.user_email}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge tone={member.role === 'OWNER' ? 'brand' : 'neutral'}>{member.role_label}</Badge>
                  {canManage && member.role !== 'OWNER' && (
                    <button
                      type="button"
                      onClick={() => setToRemove(member)}
                      className="rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                      aria-label={`Retirer ${member.user_email}`}
                    >
                      <Trash2 className="size-4" />
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
        {removal.isError && <Alert tone="error">{removal.error.message}</Alert>}

        {canManage ? (
          <form onSubmit={onAdd} noValidate className="space-y-3 border-t border-slate-100 pt-4">
            <p className="text-sm font-medium text-slate-800">Inviter un membre</p>
            <p className="text-xs text-slate-500">
              La personne doit déjà avoir un compte. Un expert obtient un accès en lecture seule ; un gestionnaire peut modifier les données.
            </p>
            {serverError && <Alert tone="error">{serverError}</Alert>}
            <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
              <TextField label="Adresse e-mail" type="email" required error={errors.email?.message} {...register('email')} />
              <SelectField
                label="Rôle"
                options={[
                  { value: 'EXPERT', label: 'Expert (lecture seule)' },
                  { value: 'MANAGER', label: 'Gestionnaire' },
                ]}
                error={errors.role?.message}
                {...register('role')}
              />
            </div>
            <div className="flex justify-end">
              <Button type="submit" size="sm" loading={isSubmitting} icon={<UserPlus className="size-4" />}>
                Inviter
              </Button>
            </div>
          </form>
        ) : (
          <p className="text-xs text-slate-500">Seul le propriétaire peut gérer les membres de cette exploitation.</p>
        )}
      </div>

      <ConfirmDialog
        open={toRemove !== null}
        title="Retirer ce membre ?"
        message={
          <>
            <strong>{toRemove?.user_email}</strong> n'aura plus accès aux données de l'exploitation « {farm.name} ».
          </>
        }
        confirmLabel="Retirer"
        danger
        loading={removal.isPending}
        onConfirm={() => toRemove && removal.mutate(toRemove)}
        onCancel={() => setToRemove(null)}
      />
    </Modal>
  )
}

export function FarmsPanel() {
  const { user } = useAuth()
  const farms = useQuery({ queryKey: ['farms'], queryFn: farmService.list })
  const [editing, setEditing] = useState<Farm | 'new' | null>(null)
  const [membersOf, setMembersOf] = useState<Farm | null>(null)
  const canCreate = user?.role === 'ELEVEUR' || user?.is_platform_admin

  return (
    <Card
      title="Mes exploitations"
      actions={
        canCreate && (
          <Button size="sm" variant="secondary" icon={<Plus className="size-4" />} onClick={() => setEditing('new')}>
            Ajouter
          </Button>
        )
      }
    >
      <div id="exploitations">
        {farms.isPending ? (
          <Spinner />
        ) : farms.isError ? (
          <Alert tone="error">{farms.error.message}</Alert>
        ) : farms.data.results.length === 0 ? (
          <EmptyState title="Aucune exploitation">
            {user?.role === 'EXPERT' ? "Vous n'avez été invité dans aucune exploitation." : 'Ajoutez votre exploitation pour commencer.'}
          </EmptyState>
        ) : (
          <ul className="divide-y divide-slate-100">
            {farms.data.results.map((farm) => {
              const canWrite = farm.my_role === 'OWNER' || farm.my_role === 'MANAGER' || user?.is_platform_admin
              return (
                <li key={farm.id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                  <div className="min-w-0">
                    <p className="font-medium text-slate-800">{farm.name}</p>
                    <p className="text-sm text-slate-500">
                      {[farm.locality, farm.region].filter(Boolean).join(' · ') || 'Localisation non renseignée'} · {farm.members_count} membre
                      {farm.members_count > 1 ? 's' : ''}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {farm.my_role_label && <Badge tone="brand">{farm.my_role_label}</Badge>}
                    <Button size="sm" variant="ghost" icon={<Users className="size-4" />} onClick={() => setMembersOf(farm)}>
                      Membres
                    </Button>
                    {canWrite && (
                      <Button size="sm" variant="secondary" onClick={() => setEditing(farm)}>
                        Modifier
                      </Button>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <FarmFormModal open={editing !== null} farm={editing === 'new' || editing === null ? undefined : editing} onClose={() => setEditing(null)} />
      {membersOf && <MembersModal open farm={membersOf} onClose={() => setMembersOf(null)} />}
    </Card>
  )
}
