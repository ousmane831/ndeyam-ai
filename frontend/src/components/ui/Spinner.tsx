import { LoaderCircle } from 'lucide-react'
import clsx from 'clsx'
import { useTranslation } from 'react-i18next'

export function Spinner({ label, className }: { label?: string; className?: string }) {
  const { t } = useTranslation()
  return (
    <span role="status" className={clsx('inline-flex items-center gap-2 text-sm text-slate-500', className)}>
      <LoaderCircle className="size-4 animate-spin" aria-hidden />
      {label ?? t('Chargement…')}
    </span>
  )
}
