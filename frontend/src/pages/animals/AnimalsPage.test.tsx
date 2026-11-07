import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { animalService, groupService, nomenclatureService } from '@/services/animals'
import { breeder, fakeAuth, fakeFarm, renderWithProviders } from '@/test/utils'
import type { Animal } from '@/types/animal'
import { AnimalsPage } from './AnimalsPage'

const animal: Animal = {
  id: 7, uuid: 'u', farm: 1, tag_number: 'SN-007', name: 'Bélier', species: 1, species_name: 'Ovin', breed: 2,
  breed_name: 'Touabire', sex: 'M', sex_label: 'Mâle', birth_date: '2026-01-01', birth_date_is_estimated: true,
  age_days: 200, initial_weight_kg: '20.00', last_weight: { weight_kg: '31.50', weighed_on: '2026-11-01', unit: 'kg' },
  category: null, category_name: null, physiological_stage: null, physiological_stage_name: null, group: null,
  group_name: null, registered_on: '2026-02-01', observations: '', status: 'ACTIVE', status_label: 'Présent',
  archived_at: null, is_demo: false, created_at: '', updated_at: '',
}

const page = (results: Animal[]) => ({ count: results.length, next: null, previous: null, results })

describe('AnimalsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(nomenclatureService, 'species').mockResolvedValue([])
    vi.spyOn(nomenclatureService, 'breeds').mockResolvedValue([])
    vi.spyOn(groupService, 'list').mockResolvedValue({ count: 0, next: null, previous: null, results: [] })
  })

  it('affiche les animaux renvoyés par l’API', async () => {
    vi.spyOn(animalService, 'list').mockResolvedValue(page([animal]))
    renderWithProviders(<AnimalsPage />, { auth: fakeAuth({ status: 'authenticated', user: breeder }) })
    expect(await screen.findByRole('link', { name: 'SN-007' })).toHaveAttribute('href', '/animaux/7')
    expect(screen.getByText('31,5 kg')).toBeInTheDocument()
    expect(screen.getByText('≈ 6 mois')).toBeInTheDocument()
  })

  it('propose d’ajouter un premier animal quand la liste est vide', async () => {
    vi.spyOn(animalService, 'list').mockResolvedValue(page([]))
    renderWithProviders(<AnimalsPage />)
    expect(await screen.findByText('Aucun animal enregistré')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ajouter mon premier animal' })).toBeInTheDocument()
  })

  it('n’affiche aucun bouton d’ajout ou d’import en lecture seule', async () => {
    vi.spyOn(animalService, 'list').mockResolvedValue(page([]))
    renderWithProviders(<AnimalsPage />, { farm: fakeFarm({ writableFarms: [] }) })
    await screen.findByText('Aucun animal enregistré')
    expect(screen.queryByRole('button', { name: /Ajouter/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Importer' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Exporter' })).toBeInTheDocument()
  })

  it('transmet l’exploitation sélectionnée à l’API', async () => {
    const list = vi.spyOn(animalService, 'list').mockResolvedValue(page([]))
    renderWithProviders(<AnimalsPage />)
    await screen.findByText('Aucun animal enregistré')
    expect(list).toHaveBeenCalledWith(expect.objectContaining({ farm: 1, page: 1 }))
  })
})
