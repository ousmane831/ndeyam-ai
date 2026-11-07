import { useContext } from 'react'
import { FarmContext, type FarmContextValue } from '@/contexts/farm-context'

export function useFarm(): FarmContextValue {
  const context = useContext(FarmContext)
  if (!context) throw new Error('useFarm doit être utilisé dans un FarmProvider.')
  return context
}
