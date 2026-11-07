import { LoaderCircle } from 'lucide-react'
import clsx from 'clsx'

export function Spinner({ label = 'Chargement…', className }: { label?: string; className?: string }) {
  return (
    <span role="status" className={clsx('inline-flex items-center gap-2 text-sm text-slate-500', className)}>
      <LoaderCircle className="size-4 animate-spin" aria-hidden />
      {label}
    </span>
  )
}
