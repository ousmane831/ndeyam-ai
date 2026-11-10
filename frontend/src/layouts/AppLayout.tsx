import clsx from 'clsx'
import { InstallAppButton } from '@/features/pwa/InstallAppButton'
import { OfflineSync } from '@/features/offline/OfflineSync'
import { Bell, BookOpen, Calculator, ClipboardList, ExternalLink, FileSearch, FileText, Layers, LayoutDashboard, LogOut, Menu, PawPrint, Settings, TrendingUp, Users, Wheat, X } from 'lucide-react'
import { Suspense, useState, type ReactNode } from 'react'
import { NavLink, Outlet } from 'react-router'
import { FarmSelector } from '@/components/FarmSelector'
import { Badge } from '@/components/ui/Feedback'
import { Wordmark } from '@/components/ui/Logo'
import { Spinner } from '@/components/ui/Spinner'
import { AssistantLauncher } from '@/features/assistant/AssistantLauncher'
import { useAuth } from '@/hooks/useAuth'

interface NavItem {
  to: string
  label: string
  icon: ReactNode
}

/*
 * Seuls les modules réellement disponibles apparaissent dans la navigation.
 * Les autres entrées du cahier des charges (animaux, ingrédients, formulation…)
 * sont ajoutées au fur et à mesure de leur développement.
 */
const MAIN_NAV: NavItem[] = [
  { to: '/', label: 'Tableau de bord', icon: <LayoutDashboard className="size-5" /> },
  { to: '/animaux', label: 'Mes animaux', icon: <PawPrint className="size-5" /> },
  { to: '/troupeaux', label: 'Mes troupeaux', icon: <Layers className="size-5" /> },
  { to: '/ingredients', label: 'Ingrédients alimentaires', icon: <Wheat className="size-5" /> },
  { to: '/formulation', label: 'Formulation des aliments', icon: <Calculator className="size-5" /> },
  { to: '/suivi-croissance', label: 'Suivi de croissance', icon: <TrendingUp className="size-5" /> },
  { to: '/rations', label: 'Historique des rations', icon: <ClipboardList className="size-5" /> },
  { to: '/alertes', label: 'Alertes et rappels', icon: <Bell className="size-5" /> },
  { to: '/references', label: 'Références nutritionnelles', icon: <BookOpen className="size-5" /> },
  { to: '/documents', label: 'Base documentaire', icon: <FileText className="size-5" /> },
  { to: '/parametres', label: 'Paramètres', icon: <Settings className="size-5" /> },
]

const ADMIN_NAV: NavItem[] = [{ to: '/administration/utilisateurs', label: 'Utilisateurs', icon: <Users className="size-5" /> }]
const REVIEW_NAV: NavItem[] = [{ to: '/tracabilite', label: 'Traçabilité des données', icon: <FileSearch className="size-5" /> }]

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

function NavSection({ title, items, onNavigate }: { title?: string; items: NavItem[]; onNavigate: () => void }) {
  return (
    <div className="space-y-1">
      {title && <p className="px-3 pt-5 pb-1.5 font-mono text-xs font-semibold tracking-[0.1em] text-brand-300 uppercase">{title}</p>}
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          onClick={onNavigate}
          className={({ isActive }) =>
            clsx(
              'flex items-center gap-3 rounded-md px-3 py-2 text-[14.5px] font-medium transition-colors [&>svg]:shrink-0',
              isActive
                ? 'bg-white/[0.08] text-white [&>svg]:text-mil-300'
                : 'text-brand-100/85 hover:bg-white/[0.05] hover:text-white [&>svg]:text-brand-300',
            )
          }
        >
          {item.icon}
          {item.label}
        </NavLink>
      ))}
    </div>
  )
}

export function AppLayout() {
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const closeMenu = () => setMenuOpen(false)

  const handleLogout = async () => {
    setLoggingOut(true)
    await logout()
  }

  const sidebar = (
    <div className="flex h-full flex-col bg-brand-900 pb-5">
      <div className="px-6 pt-6 pb-5">
        <Wordmark tone="light" />
      </div>
      <div className="weave-dark mb-4" aria-hidden />
      <nav className="flex-1 overflow-y-auto px-3" aria-label="Navigation principale">
        <NavSection items={MAIN_NAV} onNavigate={closeMenu} />
        {(user?.is_platform_admin || user?.role === 'EXPERT') && (
          <NavSection title="Référentiel" items={REVIEW_NAV} onNavigate={closeMenu} />
        )}
        {user?.is_platform_admin && (
          <>
            <NavSection title="Administration" items={ADMIN_NAV} onNavigate={closeMenu} />
            <a
              href={`${BACKEND_URL}/admin/`}
              target="_blank"
              rel="noreferrer"
              className="mt-1 flex items-center gap-3 rounded-md px-3 py-2 text-[14.5px] font-medium text-brand-100/85 hover:bg-white/[0.05] hover:text-white [&>svg]:text-brand-300"
            >
              <ExternalLink className="size-5" />
              Administration des données
            </a>
          </>
        )}
      </nav>
      <InstallAppButton />
      <p className="px-6 pt-3 font-mono text-xs tracking-[0.06em] text-brand-300 uppercase">Prototype · v0.1</p>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Barre latérale fixe (ordinateur) */}
      <aside className="fixed inset-y-0 left-0 hidden w-64 lg:block">{sidebar}</aside>

      {/* Tiroir (tablette / téléphone) */}
      {menuOpen && (
        <div className="fixed inset-0 z-[60] lg:hidden">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setMenuOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72">{sidebar}</aside>
          <button
            type="button"
            onClick={() => setMenuOpen(false)}
            className="absolute top-4 left-72 ml-2 rounded-lg bg-white p-2 text-slate-600"
            aria-label="Fermer le menu"
          >
            <X className="size-5" />
          </button>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200 bg-white px-4 sm:px-6">
          <button
            type="button"
            onClick={() => setMenuOpen(true)}
            className="rounded-md p-2.5 text-slate-600 hover:bg-slate-100 lg:hidden"
            aria-label="Ouvrir le menu"
          >
            <Menu className="size-5" />
          </button>
          <FarmSelector />
          <div className="flex-1" />
          <div className="hidden text-right md:block">
            <p className="text-sm font-semibold text-slate-800">{user ? `${user.first_name} ${user.last_name}`.trim() || user.email : ''}</p>
            <p className="text-xs text-slate-500">{user?.email}</p>
          </div>
          {user && <span className="hidden sm:inline-flex"><Badge tone={user.is_platform_admin ? 'warning' : 'indigo'}>{user.role_label}</Badge></span>}
          <button
            type="button"
            onClick={handleLogout}
            disabled={loggingOut}
            className="inline-flex min-h-11 items-center gap-2 rounded-md px-3 text-sm font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-50"
          >
            <LogOut className="size-4" />
            <span className="hidden sm:inline">Déconnexion</span>
          </button>
        </header>
        <main className="mx-auto max-w-6xl px-4 pt-6 pb-28 sm:px-6 sm:pt-8">
          <div className="mb-4 empty:hidden"><OfflineSync /></div>
          {/* Suspense local : la barre latérale reste affichée pendant le chargement d'une page. */}
          <Suspense fallback={<Spinner label="Chargement de la page…" />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
      <AssistantLauncher />
    </div>
  )
}
