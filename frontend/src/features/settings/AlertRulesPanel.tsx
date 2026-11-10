import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Alert, Card } from '@/components/ui/Feedback'
import { useFarm } from '@/hooks/useFarm'
import { alertService } from '@/services/alerts'
import type { AlertRuleDefinition } from '@/types/alert'
import { useTranslation } from 'react-i18next'

function RuleRow({ def, farmId }: { def: AlertRuleDefinition; farmId: number }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const rules = useQuery({ queryKey: ['alert-rules'], queryFn: alertService.rules })
  const existing = rules.data?.find((r) => r.farm === farmId && r.alert_type === def.alert_type)
  const platform = rules.data?.find((r) => r.farm === null && r.alert_type === def.alert_type)
  const effective = existing ?? platform
  const [active, setActive] = useState<boolean | null>(null)
  const [values, setValues] = useState<Record<string, string>>({})
  const [message, setMessage] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  const isActive = active ?? effective?.is_active ?? true
  const valueOf = (name: string, fallback: number) => values[name] ?? String(effective?.parameters[name] ?? fallback)

  const save = async () => {
    setMessage(null)
    const parameters: Record<string, number> = {}
    for (const p of def.parameters) {
      const n = Number(valueOf(p.name, p.default))
      if (!Number.isInteger(n) || n < p.min || n > p.max) {
        setMessage({ tone: 'error', text: t('{{label}} : nombre entier entre {{min}} et {{max}}.', { label: t(p.label), min: p.min, max: p.max }) })
        return
      }
      parameters[p.name] = n
    }
    setBusy(true)
    try {
      await alertService.saveRule({ id: existing?.id, farm: farmId, alert_type: def.alert_type, parameters, is_active: isActive })
      await queryClient.invalidateQueries({ queryKey: ['alert-rules'] })
      setMessage({ tone: 'success', text: t('Réglage enregistré.') })
    } catch (e) {
      setMessage({ tone: 'error', text: e instanceof Error ? e.message : t('Enregistrement impossible.') })
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="space-y-3 py-4 first:pt-0 last:pb-0">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-800">{t(def.name)}</p>
          <p className="text-sm text-slate-500">{t(def.description)}</p>
        </div>
        <label className="inline-flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" className="size-5 accent-brand-700" checked={isActive} onChange={(e) => setActive(e.target.checked)} />
          {t('Activée')}
        </label>
      </div>
      <div className="flex flex-wrap items-end gap-3">
        {def.parameters.map((p) => (
          <label key={p.name} className="text-sm text-slate-700">
            <span className="mb-1 block">{t(p.label)}</span>
            <input
              type="number"
              min={p.min}
              max={p.max}
              value={valueOf(p.name, p.default)}
              onChange={(e) => setValues((v) => ({ ...v, [p.name]: e.target.value }))}
              className="w-28 rounded-lg border border-slate-300 px-2 py-1.5"
            />
          </label>
        ))}
        <Button size="sm" variant="secondary" onClick={save} loading={busy}>
          {t('Enregistrer')}
        </Button>
      </div>
      {message && <Alert tone={message.tone}>{message.text}</Alert>}
    </li>
  )
}

export function AlertRulesPanel() {
  const { t } = useTranslation()
  const { writableFarms, defaultWritableFarmId } = useFarm()
  const [farmId, setFarmId] = useState<number | null>(defaultWritableFarmId)
  const definitions = useQuery({ queryKey: ['alert-definitions'], queryFn: alertService.definitions, staleTime: Infinity })
  if (writableFarms.length === 0 || farmId === null) return null
  const farmDefs = definitions.data?.filter((d) => d.alert_type !== 'REFERENCE_TO_VALIDATE') ?? []

  return (
    <Card
      title={t('Réglages des alertes')}
      actions={
        writableFarms.length > 1 && (
          <select aria-label={t('Exploitation des réglages')} value={farmId} onChange={(e) => setFarmId(Number(e.target.value))}
            className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm">
            {writableFarms.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        )
      }
    >
      <p className="mb-4 text-xs text-slate-500">
        {t('Ces délais organisent votre suivi ; ce ne sont pas des recommandations zootechniques. Les alertes de croissance ne reposent que sur des plages validées par un expert.')}
      </p>
      {definitions.isError ? (
        <Alert tone="error">{definitions.error.message}</Alert>
      ) : (
        <ul className="divide-y divide-slate-100">
          {farmDefs.map((d) => (
            <RuleRow key={`${farmId}-${d.alert_type}`} def={d} farmId={farmId} />
          ))}
        </ul>
      )}
    </Card>
  )
}
