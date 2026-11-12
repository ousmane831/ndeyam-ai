import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { groupService } from '@/services/animals'
import { availabilityService, seasonService } from '@/services/seasons'
import { formulaService, templateService } from '@/services/formulas'
import { ingredientService, nutritionService, priceService } from '@/services/nutrition'
import { onlineManager } from '@tanstack/react-query'
import demoPack from '@/features/offline/demo-pack.fixture.json'
import { outbox, setOutboxUser } from '@/features/offline/outbox'
import { farmA, fakeFarm, renderWithProviders } from '@/test/utils'
import type { Ingredient } from '@/types/nutrition'
import { QuickForm } from './QuickForm'

const ingredient = (id: number, name: string, ready: boolean) => ({
  id, name, local_names: '', category: 1, category_name: 'Tourteaux', category_code: 'TOURTEAUX', description: '', farm: null,
  scope: 'catalog', observations: '', is_active: true, created_at: '', ready_for_engine: ready, is_demo: false, status: 'VALIDATED',
}) as unknown as Ingredient

describe('QuickForm', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
    sessionStorage.clear()
    vi.spyOn(groupService, 'list').mockResolvedValue({ count: 2, next: null, previous: null, results: [
      { id: 4, name: 'Embouche Tabaski', animals_count: 6 }, { id: 5, name: 'Lot vide', animals_count: 0 },
    ] } as never)
    vi.spyOn(nutritionService, 'objectives').mockResolvedValue([{ id: 9, name: 'Préparation à la Tabaski' }])
    vi.spyOn(ingredientService, 'all').mockResolvedValue([ingredient(1, 'Tourteau', true), ingredient(2, 'Son', true), ingredient(3, 'Sans MS', false)])
    vi.spyOn(priceService, 'list').mockImplementation(async (params) =>
      (params.season ? [] : [{ ingredient: 1, price_per_kg_as_fed: '300.00', currency: 'XOF' }]) as never)
    const hot = { id: 2, code: 'SECHE_CHAUDE', name: 'Saison sèche chaude (soudure)', start_month: 3, end_month: 6, months: [3, 4, 5, 6], is_hot: true, description: '', sort_order: 20 }
    vi.spyOn(seasonService, 'list').mockResolvedValue([hot])
    vi.spyOn(seasonService, 'current').mockResolvedValue({ date: '2026-04-10', season: hot, next_season: null, advice: [], pending_advice: 0 })
    vi.spyOn(templateService, 'matching').mockResolvedValue([])
    vi.spyOn(availabilityService, 'list').mockResolvedValue([{ id: 1, farm: 1, ingredient: 2, season: 2, level: 'SCARCE' } as never])
  })

  it('calcule une ration pour un lot en deux gestes, sans profil à saisir', async () => {
    const calculate = vi.spyOn(formulaService, 'calculate').mockResolvedValue({ formula: { id: 42 } } as never)
    renderWithProviders(<QuickForm />, { extraRoutes: [{ path: '/formulation/:id', element: <p>résultat</p> }] })
    fireEvent.click(await screen.findByRole('radio', { name: /Embouche Tabaski/ }))
    expect(screen.queryByRole('radio', { name: /Lot vide/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('checkbox', { name: 'Sans MS' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('radio', { name: 'Préparation à la Tabaski' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Tourteau' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Son' }))
    expect(screen.getByText(/Son sera exclu du calcul économique/)).toBeInTheDocument()
    expect(screen.getByText('Rare en cette saison')).toBeInTheDocument() // disponibilité déclarée pour la saison
    fireEvent.click(screen.getByRole('button', { name: 'Calculer la ration' }))
    expect(await screen.findByText('résultat')).toBeInTheDocument()
    const payload = calculate.mock.calls[0][0]
    expect(payload).toMatchObject({ farm: 1, group: 4, objective: 9, season: 2, mode: 'ECONOMIC', ingredients: [{ ingredient: 1 }, { ingredient: 2 }] })
    expect(payload.name).toMatch(/^Ration Embouche Tabaski — \d{2}\/\d{2}\/\d{4}$/)
    expect(payload).not.toHaveProperty('species')
    // Aliments et objectif du lot sont retenus pour la prochaine fois, sur cet appareil.
    expect(JSON.parse(localStorage.getItem('ndeyam.formule-rapide.1') ?? '{}')).toEqual({ ingredients: [1, 2], objectives: { 4: '9' } })
  })

  it('demande le lot avant de calculer', async () => {
    const calculate = vi.spyOn(formulaService, 'calculate')
    renderWithProviders(<QuickForm />)
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Tourteau' }))
    fireEvent.click(screen.getByRole('button', { name: 'Calculer la ration' }))
    await waitFor(() => expect(screen.getByText('Choisissez le lot à nourrir.')).toBeInTheDocument())
    expect(calculate).not.toHaveBeenCalled()
  })

  it('sans réseau : calcule sur l’appareil et met le calcul officiel en attente d’envoi', async () => {
    const calculate = vi.spyOn(formulaService, 'calculate')
    const demoFarm = { ...farmA, is_demo: true }
    sessionStorage.setItem(`ndeyam.pack.${farmA.id}`, JSON.stringify(demoPack))
    setOutboxUser(5)
    onlineManager.setOnline(false)
    try {
      renderWithProviders(<QuickForm />, {
        farm: fakeFarm({ farms: [demoFarm], writableFarms: [demoFarm] }),
        extraRoutes: [{ path: '/formulation/hors-ligne/:id', element: <p>résultat hors ligne</p> }],
      })
      fireEvent.click(await screen.findByRole('radio', { name: /Embouche Tabaski/ })) // lots tirés du paquet hors ligne
      fireEvent.click(screen.getByRole('radio', { name: 'Préparation à la Tabaski' }))
      fireEvent.click(screen.getByRole('checkbox', { name: 'Son de mil' }))
      fireEvent.click(screen.getByRole('checkbox', { name: "Fane d'arachide" }))
      fireEvent.click(screen.getByRole('button', { name: 'Calculer la ration' }))
      expect(await screen.findByText('résultat hors ligne')).toBeInTheDocument()
      expect(calculate).not.toHaveBeenCalled()
      expect(outbox.list()).toMatchObject([{ kind: 'formula', payload: { mode: 'ECONOMIC', objective: 4 } }])
    } finally {
      onlineManager.setOnline(true)
      setOutboxUser(null)
    }
  })

  it('propose les rations types validées du lot, utilisables tout de suite', async () => {
    vi.spyOn(templateService, 'matching').mockResolvedValue([{
      id: 7, name: 'Embouche 35-50 kg', species: 1, species_name: 'Ovin', category: 6, category_name: "Mouton à l'embouche", physiological_stage: null,
      physiological_stage_name: null, objective: 4, objective_name: 'Préparation à la Tabaski', season: null, season_name: null, weight_min_kg: '35.00',
      weight_max_kg: '50.00', dm_intake_kg_day: '1.268', conditions: '', origin_formula: 3, is_demo: false, status: 'VALIDATED', status_label: 'Validé',
      validated_by_email: null, validated_at: null, validation_comment: '', created_at: '',
      items: [{ ingredient: 1, ingredient_name: 'Tourteau', ingredient_category: 'TOURTEAUX', inclusion_pct_dm: '25.000' }],
    }])
    const apply = vi.spyOn(templateService, 'apply').mockResolvedValue({ id: 99 } as never)
    renderWithProviders(<QuickForm />, { extraRoutes: [{ path: '/formulation/:id', element: <p>formule validée</p> }] })
    fireEvent.click(await screen.findByRole('radio', { name: /Embouche Tabaski/ }))
    expect(await screen.findByText('Embouche 35-50 kg')).toBeInTheDocument()
    expect(screen.getByText(/utilisables tout de suite/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Utiliser cette ration type' }))
    expect(await screen.findByText('formule validée')).toBeInTheDocument()
    expect(apply).toHaveBeenCalledWith(7, expect.objectContaining({ farm: 1, group: 4 }))
  })
})
