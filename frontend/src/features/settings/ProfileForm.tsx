import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Alert, Card } from '@/components/ui/Feedback'
import { TextField } from '@/components/ui/Field'
import { useAuth } from '@/hooks/useAuth'
import { authService } from '@/services/auth'
import { applyServerErrors } from '@/utils/forms'

const schema = z.object({
  first_name: z.string().trim().min(1, 'Le prénom est obligatoire.'),
  last_name: z.string().trim().min(1, 'Le nom est obligatoire.'),
  phone: z.string().trim().max(32, '32 caractères maximum.'),
})
type FormValues = z.infer<typeof schema>

export function ProfileForm() {
  const { user, setUser } = useAuth()
  const [message, setMessage] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: { first_name: user?.first_name ?? '', last_name: user?.last_name ?? '', phone: user?.phone ?? '' },
  })

  const onSubmit = handleSubmit(async (values) => {
    setMessage(null)
    try {
      const updated = await authService.updateProfile(values)
      setUser(updated)
      reset(values)
      setMessage({ tone: 'success', text: 'Profil mis à jour.' })
    } catch (error) {
      const text = applyServerErrors(error, setError, ['first_name', 'last_name', 'phone'])
      if (text) setMessage({ tone: 'error', text })
    }
  })

  return (
    <Card title="Mon profil">
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {message && <Alert tone={message.tone}>{message.text}</Alert>}
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Prénom" required error={errors.first_name?.message} {...register('first_name')} />
          <TextField label="Nom" required error={errors.last_name?.message} {...register('last_name')} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Adresse e-mail" value={user?.email ?? ''} disabled hint="Contactez un administrateur pour la modifier." readOnly />
          <TextField label="Téléphone" type="tel" error={errors.phone?.message} {...register('phone')} />
        </div>
        <TextField label="Rôle" value={user?.role_label ?? ''} disabled readOnly />
        <div className="flex justify-end">
          <Button type="submit" loading={isSubmitting} disabled={!isDirty}>
            Enregistrer
          </Button>
        </div>
      </form>
    </Card>
  )
}
