import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router'
import { Alert, Card } from '@/components/ui/Feedback'
import { FormulaStatus } from '@/features/formulation/FormulaStatus'
import { PageHeader, td, th } from '@/components/ui/Layout'
import { Spinner } from '@/components/ui/Spinner'
import { formulaService } from '@/services/formulas'
import { formatMoney, formatNumber } from '@/utils/format'

export function ComparePage() {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const ids = (params.get('ids') ?? '').split(',').map(Number).filter(Boolean)
  const data = useQuery({ queryKey: ['compare', ids], queryFn: () => formulaService.compare(ids), enabled: ids.length >= 2 })

  if (ids.length < 2) return <Alert tone="warning">{t('Sélectionnez au moins deux formules à comparer.')}</Alert>
  if (data.isPending) return <Spinner />
  if (data.isError) return <Alert tone="error">{data.error.message}</Alert>
  const formulas = data.data.formulas
  const ingredientNames = [...new Set(formulas.flatMap((f) => f.items.map((i) => i.ingredient_name)))].sort()
  const nutrientCodes = [...new Set(formulas.flatMap((f) => (f.result_snapshot.nutrients ?? []).map((n) => n.code)))]

  const row = (label: string, render: (f: (typeof formulas)[number]) => React.ReactNode) => (
    <tr key={label}><td className={`${td} font-medium text-slate-700`}>{label}</td>{formulas.map((f) => <td key={f.id} className={td}>{render(f)}</td>)}</tr>
  )

  return (
    <div className="space-y-6">
      <Link to="/formulation?onglet=formules" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"><ArrowLeft className="size-4" /> {t('Formules')}</Link>
      <PageHeader title={t('Comparaison de formules')} description={data.data.note} />
      <Card>
        <div className="-mx-5 overflow-x-auto">
          <table className="w-full">
            <thead className="border-y border-slate-200 bg-slate-50"><tr><th className={th} />{formulas.map((f) => <th key={f.id} className={th}><Link to={`/formulation/${f.id}`} className="text-brand-700 normal-case hover:underline">{f.name}</Link></th>)}</tr></thead>
            <tbody className="divide-y divide-slate-100">
              {row(t('Statut'), (f) => <FormulaStatus status={f.status} label={f.status_label} isDemo={f.is_demo} />)}
              {row(t('Mode'), (f) => t(f.mode_label))}
              {row(t('Coût / animal / j'), (f) => formatMoney(f.cost_per_day, f.currency))}
              {row(t('Coût / kg brut'), (f) => formatMoney(f.cost_per_kg_as_fed, f.currency))}
              {row(t('MS / animal / j'), (f) => (f.dm_intake_kg_day ? `${formatNumber(f.dm_intake_kg_day, 3)} kg` : t('Inconnue')))}
              {ingredientNames.map((name) => row(name, (f) => {
                const item = f.items.find((i) => i.ingredient_name === name)
                if (!item) return '—'
                const quantity = formatNumber(item.quantity_as_fed_kg, 3)
                return item.inclusion_pct_dm !== null
                  ? t('{{quantity}} kg brut ({{pct}} % MS)', { quantity, pct: formatNumber(item.inclusion_pct_dm, 1) })
                  : t('{{quantity}} kg brut', { quantity })
              }))}
              {nutrientCodes.map((code) => row(t('Apport {{code}}', { code }), (f) => {
                const n = f.result_snapshot.nutrients?.find((x) => x.code === code)
                return n && n.daily_amount !== null ? `${formatNumber(n.daily_amount, 3)} ${n.daily_unit}` : t('Inconnu')
              }))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
