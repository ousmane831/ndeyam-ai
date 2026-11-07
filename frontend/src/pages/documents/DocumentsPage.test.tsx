import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { documentService } from '@/services/documents'
import { breeder, fakeAuth, renderWithProviders } from '@/test/utils'
import { DocumentsPage } from './DocumentsPage'

const empty = { count: 0, next: null, previous: null, results: [] }

describe('DocumentsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(documentService, 'list').mockResolvedValue(empty)
    vi.spyOn(documentService, 'status').mockResolvedValue({
      embeddings_configured: false, embedding_provider: null, embedding_model: null, vector_store: 'numpy',
      message: "Aucun fournisseur d'embeddings configuré : recherche plein texte uniquement.",
    })
  })

  it("indique le mode de recherche et masque l'import pour un éleveur", async () => {
    renderWithProviders(<DocumentsPage />, { auth: fakeAuth({ status: 'authenticated', user: breeder }) })
    expect(await screen.findByText(/recherche plein texte uniquement/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Importer un PDF' })).not.toBeInTheDocument()
    expect(screen.getByText('Aucun document disponible')).toBeInTheDocument()
  })

  it('affiche les résultats avec leur citation (document, page, source)', async () => {
    const search = vi.spyOn(documentService, 'search').mockResolvedValue({
      method: 'plein_texte', warnings: [],
      results: [{ chunk_id: 1, document_id: 2, document_title: 'Guide', pages: 'p. 4', source: 'Rapport 2024', document_status: 'VALIDATED',
        is_demo: false, excerpt: 'Le tourteau se conserve au sec.', score: 0.4, method: 'plein_texte', citation: 'Guide, p. 4 — Rapport 2024' }],
    })
    renderWithProviders(<DocumentsPage />, { auth: fakeAuth({ status: 'authenticated', user: breeder }) })
    await userEvent.type(screen.getByLabelText('Recherche documentaire'), 'tourteau')
    await userEvent.click(screen.getByRole('button', { name: 'Rechercher' }))
    expect(await screen.findByText('Guide, p. 4 — Rapport 2024')).toBeInTheDocument()
    expect(screen.getByText('Le tourteau se conserve au sec.')).toBeInTheDocument()
    expect(search).toHaveBeenCalledWith('tourteau', false)
  })

  it("propose l'import et l'aperçu des brouillons aux experts", async () => {
    const expert = { ...breeder, role: 'EXPERT' as const, role_label: 'Expert' }
    renderWithProviders(<DocumentsPage />, { auth: fakeAuth({ status: 'authenticated', user: expert }) })
    expect(await screen.findByRole('button', { name: 'Importer un PDF' })).toBeInTheDocument()
    expect(screen.getByText(/Inclure les documents non validés/)).toBeInTheDocument()
  })
})
