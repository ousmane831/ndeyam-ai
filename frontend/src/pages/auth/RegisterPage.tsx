import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { Button } from '@/components/ui/Button'
import { Alert } from '@/components/ui/Feedback'
import { PasswordField, TextField } from '@/components/ui/Field'
import { useAuth } from '@/hooks/useAuth'
import { tk } from '@/i18n'
import { AuthLayout } from '@/layouts/AuthLayout'
import { applyServerErrors } from '@/utils/forms'

export const PASSWORD_HINT = 'Au moins 10 caractères, pas uniquement des chiffres, différent de vos informations personnelles.'

const schema = z
  .object({
    first_name: z.string().trim().min(1, tk('Le prénom est obligatoire.')),
    last_name: z.string().trim().min(1, tk('Le nom est obligatoire.')),
    email: z.email(tk('Saisissez une adresse e-mail valide.')),
    phone: z.string().trim().max(32, tk('32 caractères maximum.')),
    farm_name: z.string().trim().min(1, tk("Le nom de l'exploitation est obligatoire.")),
    farm_region: z.string().trim(),
    farm_locality: z.string().trim(),
    password: z.string().min(10, tk('Le mot de passe doit contenir au moins 10 caractères.')),
    password_confirm: z.string(),
  })
  .refine((v) => v.password === v.password_confirm, {
    path: ['password_confirm'],
    message: tk('Les deux mots de passe ne correspondent pas.'),
  })
type FormValues = z.infer<typeof schema>

const FIELDS = [
  'first_name',
  'last_name',
  'email',
  'phone',
  'farm_name',
  'farm_region',
  'farm_locality',
  'password',
  'password_confirm',
] as const

export function RegisterPage() {
  const { t } = useTranslation()
  const { register: registerAccount } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: Object.fromEntries(FIELDS.map((f) => [f, ''])) as FormValues,
  })

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null)
    try {
      await registerAccount(values)
      navigate('/', { replace: true })
    } catch (error) {
      setServerError(applyServerErrors(error, setError, FIELDS))
    }
  })

  return (
    <AuthLayout
      title={t('Créer un compte éleveur')}
      subtitle={t('Votre exploitation est créée en même temps que votre compte.')}
      footer={
        <>
          {t('Déjà inscrit ?')}{' '}
          <Link to="/connexion" className="font-medium text-brand-700 hover:underline">
            {t('Se connecter')}
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        {serverError && <Alert tone="error">{serverError}</Alert>}
        <fieldset className="space-y-4">
          <legend className="mb-1 text-sm font-semibold text-slate-800">{t('Vos informations')}</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label={t('Prénom')} autoComplete="given-name" required error={errors.first_name?.message} {...register('first_name')} />
            <TextField label={t('Nom', { context: 'person' })} autoComplete="family-name" required error={errors.last_name?.message} {...register('last_name')} />
          </div>
          <TextField label={t('Adresse e-mail')} type="email" autoComplete="email" required error={errors.email?.message} {...register('email')} />
          <TextField label={t('Téléphone')} type="tel" autoComplete="tel" placeholder="+221 …" error={errors.phone?.message} {...register('phone')} />
        </fieldset>

        <fieldset className="space-y-4 border-t border-slate-200 pt-5">
          <legend className="mb-1 text-sm font-semibold text-slate-800">{t('Votre exploitation')}</legend>
          <TextField label={t("Nom de l'exploitation")} required error={errors.farm_name?.message} {...register('farm_name')} />
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField label={t('Région')} placeholder={t('ex. Thiès')} error={errors.farm_region?.message} {...register('farm_region')} />
            <TextField label={t('Localité')} error={errors.farm_locality?.message} {...register('farm_locality')} />
          </div>
        </fieldset>

        <fieldset className="space-y-4 border-t border-slate-200 pt-5">
          <legend className="mb-1 text-sm font-semibold text-slate-800">{t('Sécurité')}</legend>
          <PasswordField
            label={t('Mot de passe')}
            autoComplete="new-password"
            required
            hint={t(PASSWORD_HINT)}
            error={errors.password?.message}
            {...register('password')}
          />
          <PasswordField
            label={t('Confirmer le mot de passe')}
            autoComplete="new-password"
            required
            error={errors.password_confirm?.message}
            {...register('password_confirm')}
          />
        </fieldset>

        <Button type="submit" className="w-full" loading={isSubmitting}>
          {t('Créer mon compte')}
        </Button>
      </form>
    </AuthLayout>
  )
}
