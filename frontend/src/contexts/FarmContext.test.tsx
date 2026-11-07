import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext } from '@/contexts/auth-context'
import { useFarm } from '@/hooks/useFarm'
import { farmService } from '@/services/farms'
import { breeder, fakeAuth, farmA } from '@/test/utils'
import { FarmProvider } from './FarmContext'

function DefaultFarm() {
  const { defaultWritableFarmId, isLoading } = useFarm()
  return <p>{isLoading ? 'chargement' : `défaut : ${defaultWritableFarmId}`}</p>
}

function renderProvider() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <AuthContext.Provider value={fakeAuth({ status: 'authenticated', user: breeder })}>
        <FarmProvider><DefaultFarm /></FarmProvider>
      </AuthContext.Provider>
    </QueryClientProvider>,
  )
}

describe('FarmProvider', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
  })

  it("ne propose jamais par défaut une exploitation désactivée (défaut trouvé à l'étape 11)", async () => {
    const inactive = { ...farmA, id: 7, name: 'Ancienne ferme', is_active: false, my_role: 'OWNER' as const }
    const active = { ...farmA, id: 9, name: 'Ferme active', is_active: true, my_role: 'OWNER' as const }
    vi.spyOn(farmService, 'list').mockResolvedValue({ count: 2, next: null, previous: null, results: [inactive, active] })
    renderProvider()
    expect(await screen.findByText('défaut : 9')).toBeInTheDocument()
  })
})
