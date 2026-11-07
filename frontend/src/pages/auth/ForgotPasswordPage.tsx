import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Feedback'
import { TextField } from '@/components/ui/Field'
import { AuthLayout } from '@/layouts/AuthLayout'
import { authService } from '@/services/auth'
import { applyServerErrors } from '@/utils/forms'

const schema = z.object({ email: z.email('Saisissez une adresse e-mail valide.') })
type FormValues = z.infer<typeof schema>

export function ForgotPasswordPage() {
  const [sentMessage, setSentMessage] = useState<string | null>(null)
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { email: '' } })

  const onSubmit = handleSubmit(async ({ email }) => {
    setServerError(null)
    try {
      setSentMessage(await authService.requestPasswordReset(email))
    } catch (error) {
      setServerError(applyServerErrors(error, setError, ['email']))
    }
  })

  return (
    <AuthLayout
      title="Mot de passe oublié"
      subtitle="Recevez par e-mail un lien pour choisir un nouveau mot de passe."
      footer={
        <Link to="/connexion" className="font-medium text-brand-700 hover:underline">
          Retour à la connexion
        </Link>
      }
    >
      {sentMessage ? (
        <Alert tone="success" title="Demande enregistrée">
          {sentMessage} Pensez à vérifier vos courriers indésirables.
        </Alert>
      ) : (
        <form onSubmit={onSubmit} noValidate className="space-y-5">
          {serverError && <Alert tone="error">{serverError}</Alert>}
          <TextField label="Adresse e-mail du compte" type="email" autoComplete="email" required error={errors.email?.message} {...register('email')} />
          <Button type="submit" className="w-full" loading={isSubmitting}>
            Envoyer le lien
          </Button>
        </form>
      )}
    </AuthLayout>
  )
}
