export interface HealthStatus {
  status: 'ok' | 'degraded'
  app: string
  version: string
  database: { connected: boolean; engine?: string }
  assistant: { configured: boolean; provider: string | null }
}
