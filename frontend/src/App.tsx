import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { ProtectedRoute } from './components/ProtectedRoute';
import { CompetencyDetailPage } from './pages/CompetencyDetailPage';
import { DashboardPage } from './pages/DashboardPage';
import { EvidenceLedgerPage } from './pages/EvidenceLedgerPage';
import { LearnerDashboard } from './pages/LearnerDashboard';
import { LoginPage } from './pages/LoginPage';
import { PathwayPage } from './pages/PathwayPage';
import { SimulationAttemptPage, SimulationRunPage } from './pages/SimulationRunPage';
import { SimulationsPage } from './pages/SimulationsPage';
import { SmeReviewPage } from './pages/SmeReviewPage';
import { useAuth } from './auth/AuthContext';
import { dashboardPathFor } from './routes';

function HomeRedirect() {
  const { user, initializing } = useAuth();

  if (initializing) {
    return (
      <div className="centered-state" role="status" aria-live="polite">
        <div className="spinner" aria-hidden="true" />
        <p>Loading…</p>
      </div>
    );
  }
  return <Navigate to={user ? dashboardPathFor(user.role) : '/login'} replace />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/learner"
        element={
          <ProtectedRoute allowedRoles={['learner']}>
            <AppShell>
              <LearnerDashboard />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/learner/competency/:competencyId"
        element={
          <ProtectedRoute allowedRoles={['learner']}>
            <AppShell>
              <CompetencyDetailPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/learner/pathway"
        element={
          <ProtectedRoute allowedRoles={['learner']}>
            <AppShell>
              <PathwayPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/learner/simulations"
        element={
          <ProtectedRoute allowedRoles={['learner']}>
            <AppShell>
              <SimulationsPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/learner/simulations/attempts/:attemptId"
        element={
          <ProtectedRoute allowedRoles={['learner']}>
            <AppShell>
              <SimulationAttemptPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/learner/simulations/:scenarioCode"
        element={
          <ProtectedRoute allowedRoles={['learner']}>
            <AppShell>
              <SimulationRunPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/learner/evidence"
        element={
          <ProtectedRoute allowedRoles={['learner']}>
            <AppShell>
              <EvidenceLedgerPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/sme"
        element={
          <ProtectedRoute allowedRoles={['sme']}>
            <AppShell>
              <SmeReviewPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/sme/overview"
        element={
          <ProtectedRoute allowedRoles={['sme']}>
            <AppShell>
              <DashboardPage role="sme" />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AppShell>
              <DashboardPage role="admin" />
            </AppShell>
          </ProtectedRoute>
        }
      />

      <Route path="/" element={<HomeRedirect />} />
      <Route path="*" element={<HomeRedirect />} />
    </Routes>
  );
}
