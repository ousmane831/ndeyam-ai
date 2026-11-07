import { lazy, Suspense, type ComponentType } from 'react'
import { Route, Routes } from 'react-router'
import { Spinner } from '@/components/ui/Spinner'
import { FarmProvider } from '@/contexts/FarmContext'
import { AppLayout } from '@/layouts/AppLayout'
import { LoginPage } from '@/pages/auth/LoginPage'
import { GuestRoute, ProtectedRoute, RoleRoute } from './guards'

/** Chargement à la demande : chaque page n'est téléchargée qu'à sa première ouverture. */
function page<K extends string>(loader: () => Promise<Record<K, ComponentType>>, name: K) {
  return lazy(() => loader().then((m) => ({ default: m[name] })))
}

const RegisterPage = page(() => import('@/pages/auth/RegisterPage'), 'RegisterPage')
const ForgotPasswordPage = page(() => import('@/pages/auth/ForgotPasswordPage'), 'ForgotPasswordPage')
const ResetPasswordPage = page(() => import('@/pages/auth/ResetPasswordPage'), 'ResetPasswordPage')
const SystemStatusPage = page(() => import('@/pages/SystemStatusPage'), 'SystemStatusPage')
const DashboardPage = page(() => import('@/pages/DashboardPage'), 'DashboardPage')
const AnimalsPage = page(() => import('@/pages/animals/AnimalsPage'), 'AnimalsPage')
const AnimalFormPage = page(() => import('@/pages/animals/AnimalFormPage'), 'AnimalFormPage')
const AnimalDetailPage = page(() => import('@/pages/animals/AnimalDetailPage'), 'AnimalDetailPage')
const GroupsPage = page(() => import('@/pages/groups/GroupsPage'), 'GroupsPage')
const GrowthPage = page(() => import('@/pages/growth/GrowthPage'), 'GrowthPage')
const AlertsPage = page(() => import('@/pages/alerts/AlertsPage'), 'AlertsPage')
const SettingsPage = page(() => import('@/pages/SettingsPage'), 'SettingsPage')
const AdminUsersPage = page(() => import('@/pages/admin/AdminUsersPage'), 'AdminUsersPage')
const IngredientsPage = page(() => import('@/pages/ingredients/IngredientsPage'), 'IngredientsPage')
const IngredientDetailPage = page(() => import('@/pages/ingredients/IngredientDetailPage'), 'IngredientDetailPage')
const ReferencesPage = page(() => import('@/pages/references/ReferencesPage'), 'ReferencesPage')
const ReferenceDetailPage = page(() => import('@/pages/references/ReferenceDetailPage'), 'ReferenceDetailPage')
const FormulationPage = page(() => import('@/pages/formulation/FormulationPage'), 'FormulationPage')
const FormulaPage = page(() => import('@/pages/formulation/FormulaPage'), 'FormulaPage')
const ComparePage = page(() => import('@/pages/formulation/ComparePage'), 'ComparePage')
const RationsPage = page(() => import('@/pages/feeding/RationsPage'), 'RationsPage')
const GovernancePage = page(() => import('@/pages/admin/GovernancePage'), 'GovernancePage')
const DocumentsPage = page(() => import('@/pages/documents/DocumentsPage'), 'DocumentsPage')
const AssistantPage = page(() => import('@/pages/assistant/AssistantPage'), 'AssistantPage')
const NotFoundPage = page(() => import('@/pages/NotFoundPage'), 'NotFoundPage')

const loading = (
  <div className="flex min-h-[40vh] items-center justify-center">
    <Spinner label="Chargement de la page…" />
  </div>
)

export function AppRoutes() {
  return (
    <Suspense fallback={loading}>
      <Routes>
        {/* Pages publiques */}
        <Route path="/connexion" element={<GuestRoute><LoginPage /></GuestRoute>} />
        <Route path="/inscription" element={<GuestRoute><RegisterPage /></GuestRoute>} />
        <Route path="/mot-de-passe-oublie" element={<GuestRoute><ForgotPasswordPage /></GuestRoute>} />
        <Route path="/reinitialiser-mot-de-passe" element={<ResetPasswordPage />} />
        <Route path="/statut" element={<SystemStatusPage />} />

        {/* Espace connecté */}
        <Route element={<ProtectedRoute><FarmProvider><AppLayout /></FarmProvider></ProtectedRoute>}>
          <Route index element={<DashboardPage />} />
          <Route path="animaux" element={<AnimalsPage />} />
          <Route path="animaux/nouveau" element={<AnimalFormPage />} />
          <Route path="animaux/:id" element={<AnimalDetailPage />} />
          <Route path="animaux/:id/modifier" element={<AnimalFormPage />} />
          <Route path="troupeaux" element={<GroupsPage />} />
          <Route path="suivi-croissance" element={<GrowthPage />} />
          <Route path="ingredients" element={<IngredientsPage />} />
          <Route path="ingredients/:id" element={<IngredientDetailPage />} />
          <Route path="references" element={<ReferencesPage />} />
          <Route path="references/:id" element={<ReferenceDetailPage />} />
          <Route path="formulation" element={<FormulationPage />} />
          <Route path="formulation/comparer" element={<ComparePage />} />
          <Route path="formulation/:id" element={<FormulaPage />} />
          <Route path="rations" element={<RationsPage />} />
          <Route path="alertes" element={<AlertsPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="assistant" element={<AssistantPage />} />
          <Route path="tracabilite" element={<RoleRoute roles={['ADMIN', 'EXPERT']}><GovernancePage /></RoleRoute>} />
          <Route path="parametres" element={<SettingsPage />} />
          <Route path="administration/utilisateurs" element={<RoleRoute roles={['ADMIN']}><AdminUsersPage /></RoleRoute>} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
