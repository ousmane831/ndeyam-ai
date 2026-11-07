import clsx from 'clsx'
import { AlertTriangle, CheckCircle2, Info, XCircle } from 'lucide-react'
import type { ReactNode } from 'react'

type Tone = 'info' | 'success' | 'warning' | 'error'

const TONES: Record<Tone, { box: string; icon: ReactNode }> = {
  info: { box: 'border-brand-200 bg-brand-50 text-brand-800', icon: <Info className="size-5 shrink-0" /> },
  success: { box: 'border-acacia-200 bg-acacia-50 text-acacia-800', icon: <CheckCircle2 className="size-5 shrink-0" /> },
  warning: { box: 'border-mil-200 bg-mil-50 text-mil-700', icon: <AlertTriangle className="size-5 shrink-0" /> },
  error: { box: 'border-red-200 bg-red-50 text-red-800', icon: <XCircle className="size-5 shrink-0" /> },
}

export function Alert({ tone = 'info', title, children, className }: { tone?: Tone; title?: string; children?: ReactNode; className?: string }) {
  const { box, icon } = TONES[tone]
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={clsx('flex gap-3 rounded-md border px-4 py-3 text-sm', box, className)}>
      {icon}
      <div className="min-w-0 space-y-0.5">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className="break-words">{children}</div>}
      </div>
    </div>
  )
}

/**
 * Pastilles d'information. `brand` = état positif (actif, validé, respecté) en vert acacia ;
 * `indigo` = information neutre de marque (rôle, appartenance).
 */
const BADGE_TONES = {
  neutral: 'bg-slate-100 text-slate-700',
  brand: 'bg-acacia-50 text-acacia-700 ring-1 ring-acacia-200',
  indigo: 'bg-brand-50 text-brand-700 ring-1 ring-brand-200',
  warning: 'bg-mil-50 text-mil-700 ring-1 ring-mil-200',
  danger: 'bg-red-50 text-red-700 ring-1 ring-red-200',
  demo: 'demo-hatch text-demo',
} as const

export type BadgeTone = keyof typeof BADGE_TONES

export function Badge({ tone = 'neutral', children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span className={clsx('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold', BADGE_TONES[tone])}>
      {children}
    </span>
  )
}

/**
 * Tampon de statut (validation, formules) : la traçabilité rendue visible. Le texte reste celui du
 * statut (capitales par CSS uniquement, pour les lecteurs d'écran et les tests).
 */
const STAMP_TONES = {
  ok: 'text-acacia-700 border-acacia-600',
  pending: 'text-mil-700 border-mil-500',
  danger: 'text-red-700 border-red-600',
  neutral: 'text-slate-600 border-slate-400',
  demo: 'demo-hatch text-demo border-transparent',
} as const

export type StampTone = keyof typeof STAMP_TONES

export function Stamp({ tone, children, title }: { tone: StampTone; children: ReactNode; title?: string }) {
  return (
    <span
      title={title}
      className={clsx(
        'inline-flex -rotate-1 items-center rounded-[3px] whitespace-nowrap border-[1.5px] bg-white/70 px-2 py-[3px] font-mono text-[11px] leading-none font-semibold tracking-[0.08em] uppercase',
        STAMP_TONES[tone],
      )}
    >
      {children}
    </span>
  )
}

/** Numéro d'animal présenté comme une boucle auriculaire (repère que tout éleveur connaît). */
export function AnimalTag({ children, size = 'sm' }: { children: ReactNode; size?: 'sm' | 'lg' }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center whitespace-nowrap bg-mil-300 font-mono font-semibold text-brand-900 [clip-path:polygon(14%_0,86%_0,100%_30%,100%_100%,0_100%,0_30%)]',
        size === 'lg' ? 'px-3 pt-2 pb-1 text-base' : 'px-2 pt-1 pb-0.5 text-xs',
      )}
    >
      {children}
    </span>
  )
}

export function Card({ title, actions, children, className }: { title?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={clsx('rounded-md border border-slate-200 bg-white', className)}>
      {(title || actions) && (
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-3.5">
          {title && <h2 className="font-display text-[17px] font-semibold text-slate-900">{title}</h2>}
          {actions}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  )
}

export function EmptyState({ icon, title, children, action }: { icon?: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-10 text-center">
      {icon && <div className="mb-1 text-brand-200">{icon}</div>}
      <p className="font-display text-base font-semibold text-slate-800">{title}</p>
      {children && <div className="max-w-md text-sm text-slate-500">{children}</div>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}
