import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useSearchParams } from 'react-router'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Feedback'
import { PasswordField } from '@/components/ui/Field'
import { AuthLayout } from '@/layouts/AuthLayout'
import { authService } from '@/services/auth'
import { applyServerErrors } from '@/utils/forms'
import { PASSWORD_HINT } from './RegisterPage'

const schema = z
  .object({
    new_password: z.string().min(10, 'Le mot de passe doit contenir au moins 10 caractères.'),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, { path: ['confirm'], message: 'Les deux mots de passe ne correspondent pas.' })
type FormValues = z.infer<typeof schema>

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const uid = params.get('uid') ?? ''
  const token = params.get('token') ?? ''
  const [done, setDone] = useState<string | null>(null)
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { new_password: '', confirm: '' } })

  const onSubmit = handleSubmit(async ({ new_password }) => {
    setServerError(null)
    try {
      setDone(await authService.confirmPasswordReset(uid, token, new_password))
    } catch (error) {
      setServerError(applyServerErrors(error, setError, ['new_password']))
    }
  })

  const linkInvalid = !uid || !token

  return (
    <AuthLayout title="Nouveau mot de passe" subtitle="Choisissez le nouveau mot de passe de votre compte.">
      {linkInvalid ? (
        <Alert tone="error" title="Lien incomplet">
          Ce lien de réinitialisation est incomplet.{' '}
          <Link to="/mot-de-passe-oublie" className="font-medium underline">
            Faire une nouvelle demande
          </Link>
        </Alert>
      ) : done ? (
        <div className="space-y-5">
          <Alert tone="success">{done}</Alert>
          <Link
            to="/connexion"
            className="flex w-full items-center justify-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            Se connecter
          </Link>
        </div>
      ) : (
        <form onSubmit={onSubmit} noValidate className="space-y-5">
          {serverError && (
            <Alert tone="error">
              {serverError}{' '}
              <Link to="/mot-de-passe-oublie" className="font-medium underline">
                Nouvelle demande
              </Link>
            </Alert>
          )}
          <PasswordField
            label="Nouveau mot de passe"
            autoComplete="new-password"
            required
            hint={PASSWORD_HINT}
            error={errors.new_password?.message}
            {...register('new_password')}
          />
          <PasswordField label="Confirmer" autoComplete="new-password" required error={errors.confirm?.message} {...register('confirm')} />
          <Button type="submit" className="w-full" loading={isSubmitting}>
            Enregistrer le mot de passe
          </Button>
        </form>
      )}
    </AuthLayout>
  )
}
