import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Alert, Card } from '@/components/ui/Feedback'
import { PasswordField } from '@/components/ui/Field'
import { PASSWORD_HINT } from '@/pages/auth/RegisterPage'
import { authService } from '@/services/auth'
import { applyServerErrors } from '@/utils/forms'

const schema = z
  .object({
    current_password: z.string().min(1, 'Saisissez votre mot de passe actuel.'),
    new_password: z.string().min(10, 'Le mot de passe doit contenir au moins 10 caractères.'),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, { path: ['confirm'], message: 'Les deux mots de passe ne correspondent pas.' })
type FormValues = z.infer<typeof schema>

export function PasswordForm() {
  const [message, setMessage] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { current_password: '', new_password: '', confirm: '' } })

  const onSubmit = handleSubmit(async (values) => {
    setMessage(null)
    try {
      const detail = await authService.changePassword(values.current_password, values.new_password)
      reset()
      setMessage({ tone: 'success', text: detail })
    } catch (error) {
      const text = applyServerErrors(error, setError, ['current_password', 'new_password'])
      if (text) setMessage({ tone: 'error', text })
    }
  })

  return (
    <Card title="Mot de passe">
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {message && <Alert tone={message.tone}>{message.text}</Alert>}
        <PasswordField
          label="Mot de passe actuel"
          autoComplete="current-password"
          required
          error={errors.current_password?.message}
          {...register('current_password')}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <PasswordField
            label="Nouveau mot de passe"
            autoComplete="new-password"
            required
            hint={PASSWORD_HINT}
            error={errors.new_password?.message}
            {...register('new_password')}
          />
          <PasswordField label="Confirmer" autoComplete="new-password" required error={errors.confirm?.message} {...register('confirm')} />
        </div>
        <div className="flex justify-end">
          <Button type="submit" loading={isSubmitting}>
            Changer le mot de passe
          </Button>
        </div>
      </form>
    </Card>
  )
}
