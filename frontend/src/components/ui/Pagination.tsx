import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from './Button'

export function Pagination({
  page,
  pageSize,
  count,
  onPageChange,
}: {
  page: number
  pageSize: number
  count: number
  onPageChange: (page: number) => void
}) {
  const { t } = useTranslation()
  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  if (count <= pageSize) return null
  const first = (page - 1) * pageSize + 1
  const last = Math.min(page * pageSize, count)
  return (
    <nav className="flex items-center justify-between gap-3 border-t border-slate-100 px-5 py-3 text-sm text-slate-600" aria-label={t('Pagination')}>
      <span>{t('{{first}}–{{last}} sur {{count}}', { first, last, count })}</span>
      <div className="flex gap-2">
        <Button size="sm" variant="secondary" onClick={() => onPageChange(page - 1)} disabled={page <= 1} icon={<ChevronLeft className="size-4" />}>
          {t('Précédent')}
        </Button>
        <Button size="sm" variant="secondary" onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}>
          {t('Suivant')}
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </nav>
  )
}
