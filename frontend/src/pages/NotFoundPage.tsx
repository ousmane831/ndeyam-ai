import { Link } from 'react-router'

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
      <p className="text-sm font-semibold text-brand-600">Erreur 404</p>
      <h1 className="text-2xl font-semibold text-slate-900">Page introuvable</h1>
      <p className="text-sm text-slate-500">Cette page n'existe pas ou vous n'y avez pas accès.</p>
      <Link to="/" className="mt-2 font-medium text-brand-700 hover:underline">
        Retour au tableau de bord
      </Link>
    </div>
  )
}
