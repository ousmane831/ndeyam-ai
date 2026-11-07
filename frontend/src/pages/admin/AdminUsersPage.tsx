import { zodResolver } from '@hookform/resolvers/zod'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Search, UserPlus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Alert, Badge, Card, EmptyState } from '@/components/ui/Feedback'
import { PasswordField, SelectField, TextField } from '@/components/ui/Field'
import { ConfirmDialog, Modal } from '@/components/ui/Modal'
import { Pagination } from '@/components/ui/Pagination'
import { Spinner } from '@/components/ui/Spinner'
import { useAuth } from '@/hooks/useAuth'
import { adminUserService, type AdminUserFilters } from '@/services/adminUsers'
import type { AdminUser, UserRole } from '@/types/auth'
import { applyServerErrors } from '@/utils/forms'

const PAGE_SIZE = 20
const ROLE_OPTIONS = [
  { value: 'ELEVEUR', label: 'Éleveur' },
  { value: 'EXPERT', label: 'Expert' },
  { value: 'ADMIN', label: 'Administrateur' },
]

const createSchema = z.object({
  first_name: z.string().trim().min(1, 'Le prénom est obligatoire.'),
  last_name: z.string().trim().min(1, 'Le nom est obligatoire.'),
  email: z.email('Saisissez une adresse e-mail valide.'),
  phone: z.string().trim(),
  role: z.enum(['ELEVEUR', 'EXPERT', 'ADMIN']),
  password: z.string().min(10, 'Au moins 10 caractères.'),
})
type CreateValues = z.infer<typeof createSchema>

function CreateUserModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: { first_name: '', last_name: '', email: '', phone: '', role: 'EXPERT', password: '' },
  })

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      await adminUserService.create(values)
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      reset()
      onClose()
    } catch (error) {
      setServerError(applyServerErrors(error, setError, ['first_name', 'last_name', 'email', 'phone', 'role', 'password']))
    }
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Créer un compte"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button onClick={onSubmit} loading={isSubmitting}>
            Créer
          </Button>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {serverError && <Alert tone="error">{serverError}</Alert>}
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Prénom" required error={errors.first_name?.message} {...register('first_name')} />
          <TextField label="Nom" required error={errors.last_name?.message} {...register('last_name')} />
        </div>
        <TextField label="Adresse e-mail" type="email" required error={errors.email?.message} {...register('email')} />
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Téléphone" error={errors.phone?.message} {...register('phone')} />
          <SelectField label="Rôle" options={ROLE_OPTIONS} error={errors.role?.message} {...register('role')} />
        </div>
        <PasswordField
          label="Mot de passe initial"
          required
          autoComplete="new-password"
          hint="À transmettre à la personne, qui pourra le changer dans ses paramètres."
          error={errors.password?.message}
          {...register('password')}
        />
      </form>
    </Modal>
  )
}

export function AdminUsersPage() {
  const { user: me } = useAuth()
  const queryClient = useQueryClient()
  const [filters, setFilters] = useState<AdminUserFilters>({ page: 1, search: '', role: '', is_active: '' })
  const [searchInput, setSearchInput] = useState('')
  const [creating, setCreating] = useState(false)
  const [toggling, setToggling] = useState<AdminUser | null>(null)

  // Recherche différée pour ne pas interroger l'API à chaque frappe.
  useEffect(() => {
    const timer = setTimeout(() => setFilters((f) => ({ ...f, search: searchInput, page: 1 })), 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const users = useQuery({
    queryKey: ['admin-users', filters],
    queryFn: () => adminUserService.list(filters),
    placeholderData: keepPreviousData,
  })

  const update = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Partial<Pick<AdminUser, 'role' | 'is_active'>> }) =>
      adminUserService.update(id, payload),
    onSuccess: async () => {
      setToggling(null)
      await queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Utilisateurs</h1>
          <p className="mt-1 text-sm text-slate-500">Comptes de la plateforme, rôles et accès.</p>
        </div>
        <Button icon={<UserPlus className="size-4" />} onClick={() => setCreating(true)}>
          Créer un compte
        </Button>
      </div>

      <Card>
        <div className="grid gap-3 sm:grid-cols-[1fr_180px_180px]">
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-slate-400" />
            <input
              type="search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Rechercher (nom, e-mail, téléphone)"
              aria-label="Rechercher un utilisateur"
              className="block w-full rounded-lg border border-slate-300 py-2.5 pr-3 pl-9 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
            />
          </div>
          <select
            aria-label="Filtrer par rôle"
            value={filters.role}
            onChange={(e) => setFilters((f) => ({ ...f, role: e.target.value as UserRole | '', page: 1 }))}
            className="rounded-lg border border-slate-300 px-3 py-2.5 text-sm"
          >
            <option value="">Tous les rôles</option>
            {ROLE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <select
            aria-label="Filtrer par statut"
            value={filters.is_active}
            onChange={(e) => setFilters((f) => ({ ...f, is_active: e.target.value as AdminUserFilters['is_active'], page: 1 }))}
            className="rounded-lg border border-slate-300 px-3 py-2.5 text-sm"
          >
            <option value="">Tous les statuts</option>
            <option value="true">Actifs</option>
            <option value="false">Désactivés</option>
          </select>
        </div>
      </Card>

      <section className="overflow-hidden rounded-md border border-slate-200 bg-white">
        {update.isError && <Alert tone="error" className="m-4">{update.error.message}</Alert>}
        {users.isPending ? (
          <div className="p-6">
            <Spinner />
          </div>
        ) : users.isError ? (
          <div className="p-4">
            <Alert tone="error">{users.error.message}</Alert>
          </div>
        ) : users.data.results.length === 0 ? (
          <EmptyState title="Aucun utilisateur ne correspond à ces critères." />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold tracking-wide text-slate-500 uppercase">
                  <tr>
                    <th className="px-5 py-3">Utilisateur</th>
                    <th className="px-5 py-3">Rôle</th>
                    <th className="px-5 py-3">Exploitations</th>
                    <th className="px-5 py-3">Statut</th>
                    <th className="px-5 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {users.data.results.map((u) => {
                    const isMe = u.id === me?.id
                    return (
                      <tr key={u.id} className="hover:bg-slate-50/60">
                        <td className="px-5 py-3">
                          <p className="font-medium text-slate-800">{`${u.first_name} ${u.last_name}`.trim() || '—'}</p>
                          <p className="text-xs text-slate-500">{u.email}</p>
                        </td>
                        <td className="px-5 py-3">
                          <select
                            aria-label={`Rôle de ${u.email}`}
                            value={u.role}
                            disabled={isMe || update.isPending}
                            onChange={(e) => update.mutate({ id: u.id, payload: { role: e.target.value as UserRole } })}
                            className="rounded-md border border-slate-300 px-2 py-1 text-sm disabled:bg-slate-50"
                          >
                            {ROLE_OPTIONS.map((o) => (
                              <option key={o.value} value={o.value}>
                                {o.label}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="px-5 py-3 text-slate-600">{u.farms_count}</td>
                        <td className="px-5 py-3">
                          {u.is_active ? <Badge tone="brand">Actif</Badge> : <Badge tone="danger">Désactivé</Badge>}
                        </td>
                        <td className="px-5 py-3 text-right">
                          {!isMe && (
                            <Button size="sm" variant={u.is_active ? 'secondary' : 'primary'} onClick={() => setToggling(u)}>
                              {u.is_active ? 'Désactiver' : 'Réactiver'}
                            </Button>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <Pagination
              page={filters.page ?? 1}
              pageSize={PAGE_SIZE}
              count={users.data.count}
              onPageChange={(page) => setFilters((f) => ({ ...f, page }))}
            />
          </>
        )}
      </section>

      <CreateUserModal open={creating} onClose={() => setCreating(false)} />
      <ConfirmDialog
        open={toggling !== null}
        title={toggling?.is_active ? 'Désactiver ce compte ?' : 'Réactiver ce compte ?'}
        message={
          toggling?.is_active ? (
            <>
              <strong>{toggling.email}</strong> ne pourra plus se connecter et ses sessions en cours seront révoquées. Ses données sont conservées.
            </>
          ) : (
            <>
              <strong>{toggling?.email}</strong> pourra de nouveau se connecter.
            </>
          )
        }
        confirmLabel={toggling?.is_active ? 'Désactiver' : 'Réactiver'}
        danger={toggling?.is_active}
        loading={update.isPending}
        onConfirm={() => toggling && update.mutate({ id: toggling.id, payload: { is_active: !toggling.is_active } })}
        onCancel={() => setToggling(null)}
      />
    </div>
  )
}
