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

/**
 * Compte de démonstration affiché sous le formulaire (jury, visiteurs) : données fictives uniquement.
 * Fourni par la configuration du site (VITE_DEMO_EMAIL, VITE_DEMO_PASSWORD), jamais écrit dans le code.
 */
function demoAccount(): { email: string; password: string } | null {
  const email = import.meta.env.VITE_DEMO_EMAIL
  const password = import.meta.env.VITE_DEMO_PASSWORD
  return email && password ? { email, password } : null
}

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
    setValue,
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

  const demo = demoAccount()
  const signInWithDemo = () => {
    if (!demo) return
    setValue('email', demo.email, { shouldValidate: true })
    setValue('password', demo.password, { shouldValidate: true })
    void onSubmit()
  }

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
      {demo && (
        <section aria-labelledby="demo-account" className="mt-6 rounded-md bg-mil-50 p-4 ring-1 ring-mil-100">
          <h2 id="demo-account" className="text-sm font-semibold text-slate-900">{t('Compte de démonstration')}</h2>
          <p className="mt-1 text-[13px] text-slate-600">{t('Pour découvrir NDEYAM AI avec des données fictives.')}</p>
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            <dt className="text-slate-600">{t('E-mail')}</dt>
            <dd className="font-mono break-all text-slate-900">{demo.email}</dd>
            <dt className="text-slate-600">{t('Mot de passe')}</dt>
            <dd className="font-mono break-all text-slate-900">{demo.password}</dd>
          </dl>
          <Button type="button" variant="secondary" className="mt-3 w-full" onClick={signInWithDemo} disabled={isSubmitting}>
            {t('Se connecter avec ce compte')}
          </Button>
        </section>
      )}
    </AuthLayout>
  )
}
