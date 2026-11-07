import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { vi } from 'vitest'
import { AuthContext, type AuthContextValue } from '@/contexts/auth-context'
import { FarmContext, type FarmContextValue } from '@/contexts/farm-context'
import type { Farm } from '@/types/farm'
import type { User } from '@/types/auth'

export const breeder: User = {
  id: 1,
  email: 'awa@exemple.sn',
  first_name: 'Awa',
  last_name: 'Ndiaye',
  phone: '',
  role: 'ELEVEUR',
  role_label: 'Éleveur',
  is_platform_admin: false,
  memberships: [],
  date_joined: '2026-11-07T00:00:00Z',
}

export function fakeAuth(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    status: 'anonymous',
    user: null,
    sessionExpired: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    setUser: vi.fn(),
    reloadUser: vi.fn(),
    ...overrides,
  }
}

export const farmA: Farm = {
  id: 1, name: 'Ferme de Thiès', country: 'SN', region: 'Thiès', locality: '', description: '', is_active: true,
  is_demo: false, my_role: 'OWNER', my_role_label: 'Propriétaire', members_count: 1, created_at: '', updated_at: '',
}

export function fakeFarm(overrides: Partial<FarmContextValue> = {}): FarmContextValue {
  const writable = overrides.writableFarms ?? [farmA]
  return {
    farms: [farmA],
    isLoading: false,
    selectedFarmId: farmA.id,
    selectFarm: vi.fn(),
    writableFarms: writable,
    defaultWritableFarmId: writable[0]?.id ?? null,
    canWrite: (id: number) => writable.some((f) => f.id === id),
    ...overrides,
  }
}

/** Rend un élément dans un routeur mémoire, avec des contextes d'authentification et d'exploitation contrôlés. */
export function renderWithProviders(
  ui: ReactNode,
  {
    auth = fakeAuth(),
    farm = fakeFarm(),
    route = '/',
    path,
    extraRoutes = [] as { path: string; element: ReactNode }[],
  }: { auth?: AuthContextValue; farm?: FarmContextValue; route?: string; path?: string; extraRoutes?: { path: string; element: ReactNode }[] } = {},
) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={auth}>
        <FarmContext.Provider value={farm}>
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route path={path ?? route.split('?')[0]} element={ui} />
            {extraRoutes.map((r) => (
              <Route key={r.path} path={r.path} element={r.element} />
            ))}
          </Routes>
        </MemoryRouter>
        </FarmContext.Provider>
      </AuthContext.Provider>
    </QueryClientProvider>,
  )
}
