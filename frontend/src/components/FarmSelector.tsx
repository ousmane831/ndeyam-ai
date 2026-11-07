import { useFarm } from '@/hooks/useFarm'

/** Sélecteur d'exploitation (affiché seulement si l'utilisateur en a plusieurs). */
export function FarmSelector() {
  const { farms, selectedFarmId, selectFarm } = useFarm()
  if (farms.length < 2) return null
  return (
    <select
      aria-label="Exploitation consultée"
      value={selectedFarmId ?? ''}
      onChange={(e) => selectFarm(e.target.value ? Number(e.target.value) : null)}
      className="max-w-[12rem] rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700 sm:max-w-xs"
    >
      <option value="">Toutes les exploitations</option>
      {farms.map((farm) => (
        <option key={farm.id} value={farm.id}>
          {farm.name}
          {farm.is_demo ? ' (DEMO)' : ''}
        </option>
      ))}
    </select>
  )
}
