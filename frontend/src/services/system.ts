import { t } from '@/i18n'
import type { HealthStatus } from '@/types/system'
import { api, ApiError } from './api'

export async function fetchHealth(): Promise<HealthStatus> {
  try {
    const { data } = await api.get<HealthStatus>('/health/')
    return data
  } catch (error) {
    // Un 503 renvoie quand même un état exploitable (base de données indisponible).
    if (error instanceof ApiError && error.status === 503) {
      throw new ApiError(t('Le serveur est démarré mais la base de données est inaccessible.'), 503, 'database_unavailable')
    }
    throw error
  }
}
