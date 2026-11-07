import type { ReactNode } from 'react'
import { Logo } from '@/components/ui/Logo'

export function AuthLayout({ title, subtitle, children, footer }: { title: string; subtitle?: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="relative hidden w-[42%] max-w-xl flex-col justify-between overflow-hidden bg-brand-800 p-10 text-white lg:flex">
        <div className="flex items-center gap-3">
          <Logo className="size-10" />
          <span className="text-lg font-semibold tracking-tight">NDEYAM AI</span>
        </div>
        <div className="space-y-4">
          <h2 className="text-3xl leading-tight font-semibold">
            Piloter son élevage
            <br />
            avec des données fiables.
          </h2>
          <p className="max-w-sm text-brand-100">
            Suivi individuel des animaux, formulation des aliments et maîtrise des coûts, pour les éleveurs du Sénégal et
            d'Afrique de l'Ouest.
          </p>
        </div>
        <p className="text-xs text-brand-200">Prototype en cours de développement — les résultats ne remplacent pas l'avis d'un professionnel.</p>
      </aside>

      <main className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <Logo />
            <span className="text-lg font-semibold text-brand-800">NDEYAM AI</span>
          </div>
          <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
          <div className="mt-8">{children}</div>
          {footer && <div className="mt-6 text-center text-sm text-slate-600">{footer}</div>}
        </div>
      </main>
    </div>
  )
}
