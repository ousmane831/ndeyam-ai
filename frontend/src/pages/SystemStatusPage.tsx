import { useQuery } from '@tanstack/react-query'
import { Bot, Database, RefreshCw, Server } from 'lucide-react'
import type { ReactNode } from 'react'
import { Logo } from '@/components/ui/Logo'
import { Spinner } from '@/components/ui/Spinner'
import { fetchHealth } from '@/services/system'
import type { ApiError } from '@/services/api'

/**
 * Page d'état du système (étape 1).
 * Elle interroge réellement /api/v1/health/ : aucun état n'est simulé.
 * Elle sera remplacée par la page de connexion à l'étape 3 et restera accessible sur /statut.
 */
export function SystemStatusPage() {
  const { data, error, isPending, isFetching, refetch } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    retry: false,
  })
  const apiError = error as ApiError | null

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 sm:py-16">
      <div className="mx-auto max-w-xl">
        <header className="mb-8 flex items-center gap-3">
          <Logo />
          <div>
            <h1 className="text-xl font-semibold text-brand-800">NDEYAM AI</h1>
            <p className="text-sm text-slate-500">État de la plateforme — prototype en cours de développement</p>
          </div>
        </header>

        <section className="rounded-md border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h2 className="font-medium text-slate-800">Services</h2>
            <button
              type="button"
              onClick={() => refetch()}
              disabled={isFetching}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw className={isFetching ? 'size-4 animate-spin' : 'size-4'} aria-hidden />
              Vérifier à nouveau
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {isPending ? (
              <div className="px-5 py-6">
                <Spinner label="Vérification des services…" />
              </div>
            ) : apiError || !data ? (
              <StatusRow
                icon={<Server className="size-5" />}
                label="API Django"
                ok={false}
                detail={apiError?.message ?? 'Réponse vide du serveur.'}
              />
            ) : (
              <>
                <StatusRow icon={<Server className="size-5" />} label="API Django" ok detail={`Version ${data.version}`} />
                <StatusRow
                  icon={<Database className="size-5" />}
                  label="Base de données"
                  ok={data.database.connected}
                  detail={data.database.connected ? data.database.engine ?? 'Connectée' : 'Inaccessible'}
                />
                <StatusRow
                  icon={<Bot className="size-5" />}
                  label="Assistant IA"
                  ok={data.assistant.configured}
                  warning={!data.assistant.configured}
                  detail={
                    data.assistant.configured
                      ? `Fournisseur : ${data.assistant.provider}`
                      : "Non configuré — les autres modules restent utilisables."
                  }
                />
              </>
            )}
          </div>
        </section>

        <p className="mt-6 text-center text-xs text-slate-400">
          Documentation de l'API : <a className="underline hover:text-brand-600" href="/api/docs/">/api/docs/</a>
        </p>
      </div>
    </main>
  )
}

function StatusRow({
  icon,
  label,
  ok,
  warning = false,
  detail,
}: {
  icon: ReactNode
  label: string
  ok: boolean
  warning?: boolean
  detail: string
}) {
  const tone = ok ? 'bg-brand-50 text-brand-700' : warning ? 'bg-mil-50 text-mil-700' : 'bg-red-50 text-red-700'
  const badge = ok ? 'Opérationnel' : warning ? 'Non configuré' : 'Indisponible'
  return (
    <div className="flex items-start gap-4 px-5 py-4">
      <span className="mt-0.5 text-slate-400">{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="font-medium text-slate-800">{label}</p>
        <p className="text-sm break-words text-slate-500">{detail}</p>
      </div>
      <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${tone}`}>{badge}</span>
    </div>
  )
}
