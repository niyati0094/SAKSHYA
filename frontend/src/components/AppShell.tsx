import { NavLink, useNavigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '../auth/AuthContext';
import { ROLE_LABELS, dashboardPathFor } from '../routes';

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return <>{children}</>;

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="shell">
      <header className="shell-header">
        <div className="shell-header-inner">
          <NavLink to={dashboardPathFor(user.role)} className="brand">
            <span className="brand-mark" aria-hidden="true">
              सा
            </span>
            <span className="brand-text">
              <strong>SAKSHYA</strong>
              <small>Competency Intelligence</small>
            </span>
          </NavLink>

          <nav className="shell-nav" aria-label="Main navigation">
            <NavLink to={dashboardPathFor(user.role)} end className="nav-link">
              {user.role === 'learner' ? 'Competency profile' : 'Dashboard'}
            </NavLink>
            {user.role === 'learner' && (
              <NavLink to="/learner/evidence" className="nav-link">
                Evidence ledger
              </NavLink>
            )}
          </nav>

          <div className="shell-user">
            <div className="shell-user-detail">
              <span className="shell-user-name">{user.full_name}</span>
              <span className={`role-badge role-${user.role}`}>{ROLE_LABELS[user.role]}</span>
            </div>
            <button type="button" className="btn btn-ghost" onClick={handleLogout}>
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="prototype-banner" role="note">
        <strong>Prototype</strong>
        <span>
          Sample data for demonstration only — not official Government of India competency data.
        </span>
      </div>

      <main className="shell-main">{children}</main>
    </div>
  );
}
