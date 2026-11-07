import type { ReactNode } from 'react'
import { Wordmark } from '@/components/ui/Logo'

const PROMISES = [
  { label: 'Nourrir', text: 'des rations calculées à partir de références validées et sourcées' },
  { label: 'Suivre', text: 'chaque animal : pesées, croissance, historique alimentaire' },
  { label: 'Maîtriser', text: "le coût réel de l'alimentation, distribution par distribution" },
]

export function AuthLayout({ title, subtitle, children, footer }: { title: string; subtitle?: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-white">
      <aside className="relative hidden w-[44%] max-w-[560px] flex-col bg-brand-900 text-white lg:flex">
        <div className="weave-dark" aria-hidden />
        <div className="flex flex-1 flex-col justify-between p-12">
          <Wordmark tone="light" size="lg" />
          <div className="space-y-10">
            <h2 className="font-display text-[40px] leading-[1.05] font-bold tracking-[-0.015em]">
              L'élevage se pilote
              <br />
              <span className="text-mil-300">avec des données justes.</span>
            </h2>
            <dl className="space-y-5">
              {PROMISES.map((p) => (
                <div key={p.label} className="grid grid-cols-[96px_1fr] gap-4 border-t border-white/10 pt-4">
                  <dt className="font-mono text-xs font-semibold tracking-[0.12em] text-mil-300 uppercase">{p.label}</dt>
                  <dd className="text-[15px] leading-snug text-brand-100">{p.text}</dd>
                </div>
              ))}
            </dl>
          </div>
          <p className="max-w-md text-xs leading-relaxed text-brand-300">
            Pour les éleveurs du Sénégal et d'Afrique de l'Ouest. Prototype : les résultats ne remplacent pas l'avis d'un
            technicien ou d'un vétérinaire.
          </p>
        </div>
      </aside>

      <main className="flex flex-1 flex-col">
        <div className="weave lg:hidden" aria-hidden />
        <div className="flex flex-1 items-center justify-center px-4 py-10 sm:px-8">
          <div className="w-full max-w-md">
            <div className="mb-10 lg:hidden">
              <Wordmark />
            </div>
            <h1 className="font-display text-[30px] leading-tight font-bold tracking-[-0.01em] text-slate-900">{title}</h1>
            {subtitle && <p className="mt-2 text-[15px] text-slate-500">{subtitle}</p>}
            <div className="mt-8">{children}</div>
            {footer && <div className="mt-8 border-t border-slate-100 pt-6 text-center text-sm text-slate-600">{footer}</div>}
          </div>
        </div>
      </main>
    </div>
  )
}
