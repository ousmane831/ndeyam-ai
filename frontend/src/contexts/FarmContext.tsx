import { useQuery } from '@tanstack/react-query'
import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { farmService } from '@/services/farms'
import type { MembershipRole } from '@/types/auth'
import { FarmContext, type FarmContextValue } from './farm-context'

const STORAGE_KEY = 'ndeyam.selectedFarm'

function readStoredFarm(): number | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? Number(raw) : null
  } catch {
    return null
  }
}

export function FarmProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const query = useQuery({ queryKey: ['farms'], queryFn: farmService.list, enabled: Boolean(user) })
  const [stored, setStored] = useState<number | null>(readStoredFarm)

  const farms = useMemo(() => query.data?.results ?? [], [query.data])
  const selectedFarmId = stored !== null && farms.some((f) => f.id === stored) ? stored : farms.length === 1 ? farms[0].id : null

  const writableFarms = useMemo(
    () => farms.filter((f) => user?.is_platform_admin || f.my_role === 'OWNER' || f.my_role === 'MANAGER'),
    [farms, user],
  )

  const selectFarm = useCallback((id: number | null) => {
    setStored(id)
    try {
      if (id === null) window.localStorage.removeItem(STORAGE_KEY)
      else window.localStorage.setItem(STORAGE_KEY, String(id))
    } catch {
      // Stockage indisponible : le choix reste valable pour la session en cours.
    }
  }, [])

  const value = useMemo<FarmContextValue>(() => {
    // Rôle de l'utilisateur dans une exploitation ; l'administrateur de la plateforme peut tout faire.
    const hasRole = (farmId: number, roles: MembershipRole[]) => {
      if (user?.is_platform_admin) return true
      const role = farms.find((f) => f.id === farmId)?.my_role
      return role != null && roles.includes(role)
    }
    const writableIds = new Set(writableFarms.map((f) => f.id))
    const selectedWritable = selectedFarmId !== null && writableIds.has(selectedFarmId) ? selectedFarmId : null
    return {
      farms,
      isLoading: query.isPending,
      selectedFarmId,
      selectFarm,
      writableFarms,
      // Sans exploitation sélectionnée : une exploitation active de préférence (jamais une désactivée par défaut).
      defaultWritableFarmId: selectedWritable ?? (writableFarms.find((f) => f.is_active) ?? writableFarms[0])?.id ?? null,
      canWrite: (farmId: number) => writableIds.has(farmId),
      canWeigh: (farmId: number) => hasRole(farmId, ['OWNER', 'MANAGER', 'TECHNICIAN']),
      canObserve: (farmId: number) => hasRole(farmId, ['OWNER', 'MANAGER', 'TECHNICIAN', 'VETERINARIAN']),
      canReviewRations: (farmId: number) => Boolean(user?.is_platform_admin) || (user?.role === 'EXPERT' && hasRole(farmId, ['EXPERT'])),
    }
  }, [farms, query.isPending, selectedFarmId, selectFarm, writableFarms, user])

  return <FarmContext.Provider value={value}>{children}</FarmContext.Provider>
}
