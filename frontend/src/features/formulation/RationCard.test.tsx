import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Formula } from '@/types/formula'
import { RationCard } from './RationCard'
import { practicalQuantity, verdictOf } from './rationText'

const formula = (over: Partial<Formula> = {}): Formula => ({
  id: 1, farm: 1, name: 'Ration lot A', species: 1, reference: 3, mode: 'ECONOMIC', mode_label: 'Économique', status: 'ESTIMATED',
  status_label: 'Estimation mathématique', is_demo: false, animal: null, group: 4, animal_weight_kg: '35.00', animal_age_months: null,
  physiological_stage: null, objective: null, dm_intake_kg_day: '1.000', as_fed_kg_day: '1.100', cost_per_day: '130.00',
  cost_per_kg_as_fed: '117.00', currency: 'XOF',
  items: [
    { id: 1, ingredient: 5, ingredient_name: '[DEMO] Son de mil', ingredient_category: 'SOUS_PRODUITS_CEREALIERS', inclusion_pct_dm: '53', inclusion_pct_as_fed: '53',
      quantity_dm_kg: '0.531', quantity_as_fed_kg: '0.590', price_per_kg_as_fed: '125.00', cost_per_day: '74.00' },
    { id: 2, ingredient: 6, ingredient_name: 'Fane arachide', ingredient_category: 'FOURRAGES', inclusion_pct_dm: '47', inclusion_pct_as_fed: '47',
      quantity_dm_kg: '0.469', quantity_as_fed_kg: '0.510', price_per_kg_as_fed: '110.00', cost_per_day: '56.00' },
  ],
  result_snapshot: { profile: { head_count: 6 } }, warnings: [], solver_status: 'Optimal', engine_version: '1.0.0',
  validated_by_email: null, validated_at: null, review_comment: '', notes: '', created_at: '2026-11-10T10:00:00Z',
  ...over,
})

describe('practicalQuantity', () => {
  it('donne des grammes sous 1 kg et des kilos au dixième au-delà', () => {
    expect(practicalQuantity(0.594)).toBe('590 g')
    expect(practicalQuantity(0.004)).toBe('10 g')
    expect(practicalQuantity(3.54)).toBe('3,5 kg')
  })
})

describe('RationCard', () => {
  it('affiche en gros les quantités et le coût du jour pour tout le lot', () => {
    render(<RationCard formula={formula()} />)
    expect(screen.getByLabelText("Nombre d'animaux")).toHaveValue('6')
    expect(screen.getByText('Son de mil')).toBeInTheDocument() // préfixe [DEMO] retiré du nom affiché
    expect(screen.getByText('3,5 kg')).toBeInTheDocument() // 0,59 kg × 6
    expect(screen.getByText('6,6 kg')).toBeInTheDocument() // total 1,1 kg × 6
    expect(screen.getByText('780 FCFA')).toBeInTheDocument() // 130 × 6
    expect(screen.getByText(/à faire vérifier par un expert avant de nourrir/)).toBeInTheDocument()
  })

  it("recalcule pour un autre nombre d'animaux et le reprend dans le message WhatsApp", () => {
    render(<RationCard formula={formula()} />)
    fireEvent.click(screen.getByRole('button', { name: 'Un animal de moins' }))
    expect(screen.getByText('650 FCFA')).toBeInTheDocument()
    const href = decodeURIComponent(screen.getByRole('link', { name: /WhatsApp/ }).getAttribute('href') ?? '')
    expect(href).toContain('Pour 5 animaux, chaque jour')
    expect(href).toContain('- Son de mil : 3 kg')
    expect(href).toContain('ESTIMATION non vérifiée par un expert')
  })

  it('dit clairement quand une ration peut être distribuée, et quand jamais', () => {
    expect(verdictOf(formula({ status: 'VALIDATED' })).tone).toBe('ok')
    expect(verdictOf(formula({ status: 'VALIDATED', is_demo: true })).text).toMatch(/ne pas utiliser/)
    expect(verdictOf(formula({ status: 'REJECTED' })).tone).toBe('stop')
  })

  it('compte un seul animal quand la formule ne vise pas un lot', () => {
    render(<RationCard formula={formula({ group: null, result_snapshot: {} })} />)
    expect(screen.getByLabelText("Nombre d'animaux")).toHaveValue('1')
    expect(screen.getByText('590 g')).toBeInTheDocument()
  })
})
