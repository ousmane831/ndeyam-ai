export type AlertSeverity = 'INFO' | 'WARNING' | 'CRITICAL'
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'DISMISSED'

export interface Alert {
  id: number
  farm: number | null
  farm_name: string | null
  alert_type: string
  alert_type_label: string
  severity: AlertSeverity
  severity_label: string
  title: string
  message: string
  rule_code: string
  rule_name: string | null
  trigger_data: Record<string, unknown>
  target: { type: string; id: number } | null
  status: AlertStatus
  status_label: string
  due_date: string | null
  resolved_at: string | null
  resolved_by_email: string | null
  created_at: string
}

export interface AlertRule {
  id: number
  farm: number | null
  scope: 'farm' | 'platform'
  alert_type: string
  alert_type_label: string
  name: string
  description: string
  parameters: Record<string, number>
  is_active: boolean
}

export interface AlertRuleDefinition {
  alert_type: string
  name: string
  description: string
  parameters: { name: string; default: number; min: number; max: number; label: string }[]
  note: string
}
