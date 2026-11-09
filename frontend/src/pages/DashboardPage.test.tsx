import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { alertService, dashboardService } from '@/services/alerts'
import * as system from '@/services/system'
import { breeder, fakeAuth, renderWithProviders } from '@/test/utils'
import type { Alert } from '@/types/alert'
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

const alert = (over: Partial<Alert>): Alert => ({
  id: 1, farm: 1, farm_name: 'Ferme', alert_type: 'WEIGHING_REMINDER', alert_type_label: 'Rappel de pesée', severity: 'WARNING',
  severity_label: 'Attention', title: 'Pesée à prévoir : SN-001', message: '', rule_code: 'weighing_interval', rule_name: null,
  trigger_data: {}, target: { type: 'animal', id: 7 }, status: 'OPEN', status_label: 'Ouverte', due_date: null, resolved_at: null,
  resolved_by_email: null, created_at: '2026-11-09T08:00:00Z', ...over,
})
const page = (results: Alert[]) => ({ count: results.length, next: null, previous: null, results })

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(system, 'fetchHealth').mockResolvedValue({
      status: 'ok', app: 'NDEYAM AI', version: '0.1.0', database: { connected: true }, assistant: { configured: false, provider: null },
    })
    vi.spyOn(alertService, 'list').mockResolvedValue(page([]))
  })

  it('affiche des états vides explicites sans inventer de statistiques', async () => {
    vi.spyOn(dashboardService, 'get').mockResolvedValue(empty)
    renderWithProviders(<DashboardPage />, { auth: fakeAuth({ status: 'authenticated', user: breeder }) })
    expect(await screen.findByText('Aucun animal enregistré')).toBeInTheDocument()
    expect(screen.getByText('Aucune distribution enregistrée')).toBeInTheDocument()
    expect(screen.getByText('Aucune pesée sur les six derniers mois')).toBeInTheDocument()
    expect(screen.queryByText(/FCFA/)).not.toBeInTheDocument()
    expect(screen.queryByText('graphique-poids')).not.toBeInTheDocument()
    expect(await screen.findByText(/Rien d'urgent/)).toBeInTheDocument()
    // L'état technique des services n'est montré qu'aux administrateurs.
    expect(screen.queryByText('Services')).not.toBeInTheDocument()
  })

  it('affiche les indicateurs réels et signale les coûts incomplets', async () => {
    vi.spyOn(dashboardService, 'get').mockResolvedValue({
      ...empty,
      animals: { total: 12, by_species: [{ code: 'OVIN', name: 'Ovin', count: 12 }], by_category: [{ name: 'Brebis', count: 12 }], by_sex: { M: 2, F: 10 } },
      weight_trend: { points: [{ month: '2026-10', mean_weight_kg: 31.2, weighings: 12, animals: 12 }], note: 'Poids moyen' },
      feeding_cost: { ...empty.feeding_cost, estimated_cost: '45000.00', records: 10, records_without_cost: 3 },
    })
    renderWithProviders(<DashboardPage />)
    const stat = (await screen.findByText('Animaux présents')).parentElement!.parentElement!
    expect(within(stat).getByText('12')).toBeInTheDocument()
    expect(screen.getByText('10 femelle(s), 2 mâle(s)')).toBeInTheDocument()
    expect(screen.getByText(/45\s?000 FCFA/)).toBeInTheDocument()
    expect(screen.getByText('3 distribution(s) sur 10 sans coût connu')).toBeInTheDocument()
    expect(screen.getByText('graphique-poids')).toBeInTheDocument()
  })

  it("transforme les alertes ouvertes en tâches du jour avec une action directe", async () => {
    vi.spyOn(dashboardService, 'get').mockResolvedValue(empty)
    vi.spyOn(alertService, 'list').mockResolvedValue(page([
      alert({ id: 1 }),
      alert({ id: 2, alert_type: 'FORMULA_TO_REVIEW', title: 'Formule en attente', target: { type: 'feedformula', id: 42 } }),
      alert({ id: 3, status: 'RESOLVED', title: 'Pesée à prévoir : SN-009' }),
    ]))
    renderWithProviders(<DashboardPage />)
    expect(await screen.findByText('1 animal à peser')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Peser/ })).toHaveAttribute('href', '/animaux/7?onglet=pesees')
    expect(screen.getByText("Formule en attente d'un expert (1)")).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Voir' })).toHaveAttribute('href', '/formulation/42')
    expect(screen.queryByText(/SN-009/)).not.toBeInTheDocument()
  })
})
