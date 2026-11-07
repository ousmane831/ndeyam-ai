import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ingredientService, priceService, sourceService } from '@/services/nutrition'
import { breeder, fakeAuth, renderWithProviders } from '@/test/utils'
import type { IngredientDetail, Nutrient } from '@/types/nutrition'
import { IngredientDetailPage } from './IngredientDetailPage'

const nutrient = (id: number, code: string, unit: string): Nutrient => ({
  id, code, name: code, category: code === 'MS' ? 'DRY_MATTER' : 'PROTEIN', category_label: '', amount_unit: 'g',
  basis: code === 'MS' ? 'AS_FED' : 'DM', unit_label: unit, system: null, system_code: null,
})

const ingredient: IngredientDetail = {
  id: 5, name: 'Son de blé', local_names: '', category: 2, category_name: 'Sous-produits céréaliers', description: '', farm: null,
  scope: 'catalog', observations: '', is_active: true, source: null, reference_date: null, is_demo: false, status: 'VALIDATED',
  status_label: 'Validé', validated_by_email: null, validated_at: null, validation_comment: '', created_at: '',
  composition_table: [
    { nutrient: nutrient(1, 'MS', 'g/kg brut'), known: true, validated_value: '880.0000', values: [] },
    { nutrient: nutrient(2, 'MAT', 'g/kg MS'), known: false, validated_value: null, values: [] },
  ],
}

describe('IngredientDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(ingredientService, 'get').mockResolvedValue(ingredient)
    vi.spyOn(priceService, 'list').mockResolvedValue([])
    vi.spyOn(sourceService, 'list').mockResolvedValue({ count: 0, next: null, previous: null, results: [] })
  })

  it('affiche la valeur validée et signale explicitement les valeurs inconnues', async () => {
    renderWithProviders(<IngredientDetailPage />, { route: '/ingredients/5', path: '/ingredients/:id', auth: fakeAuth({ status: 'authenticated', user: breeder }) })
    expect(await screen.findByText('880')).toBeInTheDocument()
    expect(screen.getByText('Inconnue')).toBeInTheDocument()
    expect(screen.getByText(/1 valeur\(s\) validée\(s\) sur 2 nutriments/)).toBeInTheDocument()
  })

  it("un éleveur ne peut pas modifier le catalogue commun mais peut saisir ses prix", async () => {
    renderWithProviders(<IngredientDetailPage />, { route: '/ingredients/5', path: '/ingredients/:id', auth: fakeAuth({ status: 'authenticated', user: breeder }) })
    await screen.findByText('880')
    expect(screen.queryByText('Ajouter une valeur')).not.toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Enregistrer le prix' })).toBeInTheDocument()
    expect(screen.getByText(/ne pourra pas être utilisé en mode économique/)).toBeInTheDocument()
  })

  it('un expert peut ajouter une valeur', async () => {
    const expert = { ...breeder, role: 'EXPERT' as const, role_label: 'Expert' }
    renderWithProviders(<IngredientDetailPage />, { route: '/ingredients/5', path: '/ingredients/:id', auth: fakeAuth({ status: 'authenticated', user: expert }) })
    expect(await screen.findByText('Ajouter une valeur')).toBeInTheDocument()
  })
})
