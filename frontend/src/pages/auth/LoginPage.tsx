import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Feedback'
import { PasswordField, TextField } from '@/components/ui/Field'
import { useAuth } from '@/hooks/useAuth'
import { AuthLayout } from '@/layouts/AuthLayout'
import { applyServerErrors } from '@/utils/forms'

const schema = z.object({
  email: z.email("Saisissez une adresse e-mail valide."),
  password: z.string().min(1, 'Saisissez votre mot de passe.'),
  remember: z.boolean(),
})
type FormValues = z.infer<typeof schema>

export function LoginPage() {
  const { login, sessionExpired } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [serverError, setServerError] = useState<string | null>(null)
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { email: '', password: '', remember: true } })

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      await login(values.email, values.password, values.remember)
      navigate(from, { replace: true })
    } catch (error) {
      setServerError(applyServerErrors(error, setError, ['email', 'password']))
    }
  })

  return (
    <AuthLayout
      title="Connexion"
      subtitle="Accédez à votre espace NDEYAM AI."
      footer={
        <>
          Pas encore de compte ?{' '}
          <Link to="/inscription" className="font-medium text-brand-700 hover:underline">
            Créer un compte éleveur
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        {sessionExpired && !serverError && <Alert tone="warning">Votre session a expiré. Veuillez vous reconnecter.</Alert>}
        {serverError && <Alert tone="error">{serverError}</Alert>}
        <TextField label="Adresse e-mail" type="email" autoComplete="email" required error={errors.email?.message} {...register('email')} />
        <PasswordField
          label="Mot de passe"
          autoComplete="current-password"
          required
          error={errors.password?.message}
          {...register('password')}
        />
        <div className="flex items-center justify-between gap-3 text-sm">
          <label className="inline-flex items-center gap-2 text-slate-600">
            <input type="checkbox" className="size-4 rounded border-slate-300 accent-brand-600" {...register('remember')} />
            Rester connecté
          </label>
          <Link to="/mot-de-passe-oublie" className="font-medium text-brand-700 hover:underline">
            Mot de passe oublié ?
          </Link>
        </div>
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Se connecter
        </Button>
      </form>
    </AuthLayout>
  )
}
