import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Feedback'
import { PasswordField, TextField } from '@/components/ui/Field'
import { useAuth } from '@/hooks/useAuth'
import { tk } from '@/i18n'
import { AuthLayout } from '@/layouts/AuthLayout'
import { applyServerErrors } from '@/utils/forms'

const schema = z.object({
  email: z.email(tk('Saisissez une adresse e-mail valide.')),
  password: z.string().min(1, tk('Saisissez votre mot de passe.')),
  remember: z.boolean(),
})
type FormValues = z.infer<typeof schema>

export function LoginPage() {
  const { t } = useTranslation()
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
      title={t('Connexion')}
      subtitle={t('Accédez à votre espace NDEYAM AI.')}
      footer={
        <>
          {t('Pas encore de compte ?')}{' '}
          <Link to="/inscription" className="font-medium text-brand-700 hover:underline">
            {t('Créer un compte éleveur')}
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        {sessionExpired && !serverError && <Alert tone="warning">{t('Votre session a expiré. Veuillez vous reconnecter.')}</Alert>}
        {serverError && <Alert tone="error">{serverError}</Alert>}
        <TextField label={t('Adresse e-mail')} type="email" autoComplete="email" required error={errors.email?.message} {...register('email')} />
        <PasswordField
          label={t('Mot de passe')}
          autoComplete="current-password"
          required
          error={errors.password?.message}
          {...register('password')}
        />
        <div className="flex items-center justify-between gap-3 text-sm">
          <label className="inline-flex items-center gap-2 text-slate-600">
            <input type="checkbox" className="size-4 rounded border-slate-300 accent-brand-600" {...register('remember')} />
            {t('Rester connecté')}
          </label>
          <Link to="/mot-de-passe-oublie" className="font-medium text-brand-700 hover:underline">
            {t('Mot de passe oublié ?')}
          </Link>
        </div>
        <Button type="submit" className="w-full" loading={isSubmitting}>
          {t('Se connecter')}
        </Button>
      </form>
    </AuthLayout>
  )
}
