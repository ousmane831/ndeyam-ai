import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { alertService } from '@/services/alerts'
import { renderWithProviders } from '@/test/utils'
import type { Alert } from '@/types/alert'
import { AlertList } from './AlertList'

const alert: Alert = {
  id: 3, farm: 1, farm_name: 'Ferme de Thiès', alert_type: 'WEIGHING_REMINDER', alert_type_label: 'Rappel de pesée',
  severity: 'INFO', severity_label: 'Information', title: 'Pesée à prévoir : SN-001',
  message: 'Dernière pesée le 01/10/2026, soit il y a 37 jours.', rule_code: 'weighing_interval', rule_name: null,
  trigger_data: { days_since: 37, interval_days: 30 }, target: { type: 'animal', id: 9 }, status: 'OPEN',
  status_label: 'Ouverte', due_date: '2026-10-31', resolved_at: null, resolved_by_email: null, created_at: '2026-11-07T08:00:00Z',
}

describe('AlertList', () => {
  beforeEach(() => vi.restoreAllMocks())

  it("explique l'alerte et renvoie vers l'animal", async () => {
    renderWithProviders(<AlertList alerts={[alert]} canAct={() => true} />)
    expect(screen.getByText('Pesée à prévoir : SN-001')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: "voir l'animal" })).toHaveAttribute('href', '/animaux/9')
    await userEvent.click(screen.getByText('Pourquoi cette alerte ?'))
    expect(screen.getByText('interval_days')).toBeInTheDocument()
    expect(screen.getByText('37')).toBeInTheDocument()
  })

  it('appelle l’API pour résoudre une alerte', async () => {
    const act = vi.spyOn(alertService, 'act').mockResolvedValue({ ...alert, status: 'RESOLVED' })
    renderWithProviders(<AlertList alerts={[alert]} canAct={() => true} />)
    await userEvent.click(screen.getByRole('button', { name: 'Résolue' }))
    expect(act).toHaveBeenCalledWith(3, 'resolve')
  })

  it('n’affiche aucune action en lecture seule', () => {
    renderWithProviders(<AlertList alerts={[alert]} canAct={() => false} />)
    expect(screen.queryByRole('button', { name: 'Résolue' })).not.toBeInTheDocument()
  })

  it('affiche un état vide explicite', () => {
    renderWithProviders(<AlertList alerts={[]} canAct={() => true} emptyTitle="Aucune alerte ouverte" />)
    expect(screen.getByText('Aucune alerte ouverte')).toBeInTheDocument()
  })
})
