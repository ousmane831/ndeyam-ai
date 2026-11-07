import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/services/api'
import * as system from '@/services/system'
import { SystemStatusPage } from './SystemStatusPage'

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <SystemStatusPage />
    </QueryClientProvider>,
  )
}

describe('SystemStatusPage', () => {
  beforeEach(() => vi.restoreAllMocks())

  it("affiche l'état renvoyé par l'API", async () => {
    vi.spyOn(system, 'fetchHealth').mockResolvedValue({
      status: 'ok',
      app: 'NDEYAM AI',
      version: '0.1.0',
      database: { connected: true, engine: 'PostgreSQL 18.6' },
      assistant: { configured: false, provider: null },
    })
    renderPage()
    expect(await screen.findByText('PostgreSQL 18.6')).toBeInTheDocument()
    expect(screen.getByText(/Non configuré — les autres modules/)).toBeInTheDocument()
  })

  it("affiche un message explicite lorsque l'API est injoignable", async () => {
    vi.spyOn(system, 'fetchHealth').mockRejectedValue(new ApiError('Impossible de joindre le serveur.', null, 'network_error'))
    renderPage()
    expect(await screen.findByText('Impossible de joindre le serveur.')).toBeInTheDocument()
    expect(screen.getByText('Indisponible')).toBeInTheDocument()
  })
})
