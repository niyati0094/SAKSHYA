import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { ApiError, useAuth } from '../auth/AuthContext';
import { dashboardPathFor } from '../routes';
import type { Role } from '../types';

/** Development-only fixtures, mirroring backend/app/db/seed.py. */
const DEMO_ACCOUNTS: { role: Role; email: string; label: string; description: string }[] = [
  {
    role: 'learner',
    email: 'learner@sakshya.dev',
    label: 'Learner',
    description: 'Competency profile, evidence and pathway',
  },
  {
    role: 'sme',
    email: 'sme@sakshya.dev',
    label: 'Subject Matter Expert',
    description: 'Review and approve generated assessments',
  },
  {
    role: 'admin',
    email: 'admin@sakshya.dev',
    label: 'Administrator',
    description: 'Organisation-wide capacity overview',
  },
];

const DEMO_PASSWORD = 'Sakshya@2026';

export function LoginPage() {
  const { user, login, initializing } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (initializing) {
    return (
      <div className="centered-state" role="status" aria-live="polite">
        <div className="spinner" aria-hidden="true" />
        <p>Loading…</p>
      </div>
    );
  }

  if (user) {
    return <Navigate to={dashboardPathFor(user.role)} replace />;
  }

  async function submit(nextEmail: string, nextPassword: string) {
    setError(null);
    setSubmitting(true);
    try {
      const authenticated = await login(nextEmail, nextPassword);
      navigate(dashboardPathFor(authenticated.role), { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Something went wrong while signing in.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-layout">
      <section className="login-pitch">
        <div className="brand brand-lg">
          <span className="brand-mark" aria-hidden="true">
            सा
          </span>
          <span className="brand-text">
            <strong>SAKSHYA</strong>
            <small>Competency Intelligence</small>
          </span>
        </div>

        <h1>Competency proven by evidence, not certificates.</h1>
        <p className="login-lede">
          SAKSHYA builds an auditable evidence trail from assessments, simulations and reviewed
          learning activity to determine what a statistical officer can actually do — and what to
          do next.
        </p>

        <ol className="chain" aria-label="How SAKSHYA works">
          <li>Role</li>
          <li>Competency</li>
          <li>Evidence</li>
          <li>Gap</li>
          <li>Intervention</li>
        </ol>

        <p className="login-footnote">
          Prototype for Smart India Hackathon 2026 — Problem Statement 26101. Sample data only.
        </p>
      </section>

      <section className="login-panel">
        <form
          className="card login-card"
          onSubmit={(event) => {
            event.preventDefault();
            void submit(email, password);
          }}
        >
          <h2>Sign in</h2>

          {error && (
            <div className="alert alert-error" role="alert">
              {error}
            </div>
          )}

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              autoComplete="username"
              required
              placeholder="you@sakshya.dev"
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              autoComplete="current-password"
              required
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="card demo-card">
          <h3>Demo accounts</h3>
          <p className="muted small">
            Development-only credentials. Select one to sign in immediately.
          </p>
          <div className="demo-list">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                className="demo-account"
                disabled={submitting}
                onClick={() => {
                  setEmail(account.email);
                  setPassword(DEMO_PASSWORD);
                  void submit(account.email, DEMO_PASSWORD);
                }}
              >
                <span className={`role-badge role-${account.role}`}>{account.label}</span>
                <span className="demo-account-desc">{account.description}</span>
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
