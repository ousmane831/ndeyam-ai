import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Formula } from '@/types/formula'
import { FormulaResult } from './FormulaResult'

const base: Formula = {
  id: 1, farm: 1, name: 'F', species: 1, reference: 3, mode: 'ECONOMIC', mode_label: 'Économique (coût minimal)', status: 'ESTIMATED',
  status_label: 'Estimation mathématique', is_demo: false, animal: null, group: null, animal_weight_kg: null, animal_age_months: null,
  physiological_stage: null, objective: null, dm_intake_kg_day: '1.000', as_fed_kg_day: '1.200', cost_per_day: '200.00',
  cost_per_kg_as_fed: '166.67', currency: 'XOF',
  items: [{ id: 1, ingredient: 5, ingredient_name: 'Maïs test', inclusion_pct_dm: '50.000', inclusion_pct_as_fed: '45.000', quantity_dm_kg: '0.5000',
    quantity_as_fed_kg: '0.5500', price_per_kg_as_fed: '100.00', cost_per_day: '55.00' }],
  result_snapshot: {
    status: 'ESTIMATED',
    nutrients: [
      { code: 'MAT', name: 'Protéines', system: null, daily_amount: 150, daily_unit: 'g/jour', concentration_dm: 150, concentration_unit: 'g/kg MS',
        complete: true, missing_for: [], requirements: [{ expression: 'DAILY_AMOUNT', min: 200, target: null, max: null, unit: 'g/jour', status: 'below' }] },
      { code: 'CA', name: 'Calcium', system: null, daily_amount: null, daily_unit: 'g/jour', concentration_dm: null, concentration_unit: 'g/kg MS',
        complete: false, missing_for: ['Maïs test'] },
    ],
    constraints: [{ constraint: 'Ingestion de matière sèche', value: 1, unit: 'kg MS/jour', min: 1, max: 1, status: 'ok' }],
    sources: ['Analyse T-01'],
    reference: { id: 3, name: 'Référence test', system: 'INRA', source: 'Tables', status: 'VALIDATED', is_demo: false },
    disclaimer: 'Estimation mathématique calculée à partir des seules données validées.',
  },
  warnings: ['« Son » exclu : teneur en matière sèche inconnue.'], solver_status: 'Optimal', engine_version: '1.0.0',
  validated_by_email: null, validated_at: null, review_comment: '', notes: '', created_at: '2026-11-07T10:00:00Z',
}

describe('FormulaResult', () => {
  it('présente une estimation avec ses limites, sans la faire passer pour une recommandation', () => {
    render(<FormulaResult formula={base} />)
    expect(screen.getByText('Estimation mathématique')).toBeInTheDocument()
    expect(screen.getByText(/seules données validées/)).toBeInTheDocument()
    expect(screen.getByText('Maïs test')).toBeInTheDocument()
    expect(screen.getByText('Insuffisant')).toBeInTheDocument()
    expect(screen.getByText('Inconnu')).toBeInTheDocument()
    expect(screen.getByText('Valeur inconnue pour : Maïs test')).toBeInTheDocument()
    expect(screen.getByText('« Son » exclu : teneur en matière sèche inconnue.')).toBeInTheDocument()
    expect(screen.getByText('Analyse T-01')).toBeInTheDocument()
    expect(screen.getByText(/Référence test \(INRA\)/)).toBeInTheDocument()
  })

  it('explique un refus et n’affiche aucune ration', () => {
    render(<FormulaResult formula={{ ...base, status: 'REFUSED', items: [], dm_intake_kg_day: null, cost_per_day: null,
      result_snapshot: { status: 'REFUSED', refusal_reasons: ['Aucune référence nutritionnelle validée ne correspond à ce profil.'] } }} />)
    expect(screen.getByText('Calcul refusé : données insuffisantes')).toBeInTheDocument()
    expect(screen.getByText(/Aucune référence nutritionnelle validée/)).toBeInTheDocument()
    expect(screen.queryByText('Composition de la ration')).not.toBeInTheDocument()
  })

  it('détaille les contraintes bloquantes d’une formule impossible', () => {
    render(<FormulaResult formula={{ ...base, status: 'INFEASIBLE', items: [], result_snapshot: {
      status: 'INFEASIBLE', refusal_reasons: ['Aucune ration ne permet de respecter simultanément toutes les contraintes.'],
      infeasibility: [{ constraint: 'MAT (apport journalier)', side: 'min', bound: 400, unit: 'g/jour', gap: 100,
        explanation: 'Minimum de 400 g/jour impossible à atteindre : il manque environ 100 g/jour.' }] } }} />)
    expect(screen.getByText('Aucune ration ne respecte toutes les contraintes')).toBeInTheDocument()
    expect(screen.getByText(/il manque environ 100 g\/jour/)).toBeInTheDocument()
  })

  it('signale une formule de démonstration', () => {
    render(<FormulaResult formula={{ ...base, is_demo: true }} />)
    expect(screen.getByText(/DÉMONSTRATION/)).toBeInTheDocument()
  })
})
