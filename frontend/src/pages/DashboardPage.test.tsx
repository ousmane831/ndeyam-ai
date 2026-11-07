import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { dashboardService } from '@/services/alerts'
import * as system from '@/services/system'
import { breeder, fakeAuth, renderWithProviders } from '@/test/utils'
import type { DashboardData } from '@/types/dashboard'
import { DashboardPage } from './DashboardPage'

vi.mock('@/components/LazyChart', () => ({
  DistributionChart: () => <div>graphique-répartition</div>,
  WeightTrendChart: () => <div>graphique-poids</div>,
  WeightChart: () => null,
}))

const empty: DashboardData = {
  farms_count: 1,
  animals: { total: 0, by_species: [], by_category: [], by_sex: { M: 0, F: 0 } },
  groups_count: 0,
  weighings: { last_30_days: 0, never_weighed: 0, latest: [] },
  weight_trend: { points: [], note: '' },
  rations: { active_count: 0, active: [] },
  feeding_cost: { period_days: 30, estimated_cost: null, distributed_kg: null, records: 0, records_without_cost: 0, currency: 'XOF' },
  alerts: { open: 0, by_severity: {}, latest: [] },
  recent_activity: [],
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(system, 'fetchHealth').mockResolvedValue({
      status: 'ok', app: 'NDEYAM AI', version: '0.1.0', database: { connected: true }, assistant: { configured: false, provider: null },
    })
  })

  it('affiche des états vides explicites sans inventer de statistiques', async () => {
    vi.spyOn(dashboardService, 'get').mockResolvedValue(empty)
    renderWithProviders(<DashboardPage />, { auth: fakeAuth({ status: 'authenticated', user: breeder }) })
    expect(await screen.findByText('Aucun animal enregistré')).toBeInTheDocument()
    expect(screen.getByText('Aucune distribution enregistrée')).toBeInTheDocument()
    expect(screen.getByText('Aucune pesée sur les six derniers mois')).toBeInTheDocument()
    expect(screen.queryByText(/FCFA/)).not.toBeInTheDocument()
    expect(screen.queryByText('graphique-poids')).not.toBeInTheDocument()
  })

  it('affiche les indicateurs réels et signale les coûts incomplets', async () => {
    vi.spyOn(dashboardService, 'get').mockResolvedValue({
      ...empty,
      animals: { total: 12, by_species: [{ code: 'OVIN', name: 'Ovin', count: 12 }], by_category: [{ name: 'Brebis', count: 12 }], by_sex: { M: 2, F: 10 } },
      weight_trend: { points: [{ month: '2026-10', mean_weight_kg: 31.2, weighings: 12, animals: 12 }], note: 'Poids moyen' },
      feeding_cost: { ...empty.feeding_cost, estimated_cost: '45000.00', records: 10, records_without_cost: 3 },
    })
    renderWithProviders(<DashboardPage />)
    expect(await screen.findByText('12')).toBeInTheDocument()
    expect(screen.getByText('10 femelle(s), 2 mâle(s)')).toBeInTheDocument()
    expect(screen.getByText(/45\s?000 FCFA/)).toBeInTheDocument()
    expect(screen.getByText('3 distribution(s) sur 10 sans coût connu')).toBeInTheDocument()
    expect(screen.getByText('graphique-poids')).toBeInTheDocument()
  })
})
