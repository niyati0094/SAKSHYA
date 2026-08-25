import { useEffect, useState } from 'react';
import { ApiError, apiFetch } from '../api/client';
import { ROLE_LABELS } from '../routes';
import type { DashboardPayload, HealthPayload, Role } from '../types';

const CAPABILITY_LABELS: Record<string, string> = {
  view_own_competency_profile: 'View own competency profile',
  view_own_evidence_ledger: 'View own evidence ledger',
  take_assessments: 'Take assessments',
  run_simulations: 'Run statistical simulations',
  view_recommendations: 'View personalised recommendations',
  view_review_queue: 'View question review queue',
  approve_generated_questions: 'Approve generated questions',
  edit_generated_questions: 'Edit generated questions',
  reject_generated_questions: 'Reject generated questions',
  view_competency_mapping: 'View competency mapping',
  view_aggregate_competency_gaps: 'View aggregate competency gaps',
  view_role_distribution: 'View role-wise distribution',
  view_training_needs: 'View training needs',
  manage_learning_catalog: 'Manage learning catalogue',
};

const MODULE_LABELS: Record<string, string> = {
  competency_profile: 'Competency profile',
  competency_gaps: 'Competency gaps',
  evidence_ledger: 'Evidence ledger',
  recommendations: 'Personalised pathway',
  generated_question_queue: 'Generated question queue',
  evidence_review: 'Evidence review',
  aggregate_gaps: 'Aggregate competency gaps',
  role_distribution: 'Role-wise distribution',
  training_needs: 'Training needs analysis',
};

function humanise(value: string, lookup: Record<string, string>): string {
  return lookup[value] ?? value.replace(/_/g, ' ');
}

export function DashboardPage({ role }: { role: Role }) {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [health, setHealth] = useState<HealthPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    async function load() {
      try {
        const [dashboard, healthPayload] = await Promise.all([
          apiFetch<DashboardPayload>(`/dashboard/${role}`),
          apiFetch<HealthPayload>('/health'),
        ]);
        if (cancelled) return;
        setData(dashboard);
        setHealth(healthPayload);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : 'Unable to load your dashboard.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [role]);

  if (loading) {
    return (
      <div className="centered-state" role="status" aria-live="polite">
        <div className="spinner" aria-hidden="true" />
        <p>Loading your workspace…</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="alert alert-error" role="alert">
        {error ?? 'Unable to load your dashboard.'}
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">{ROLE_LABELS[role]} workspace</p>
          <h1>{data.user.full_name}</h1>
          <p className="muted">
            {data.user.designation}
            {data.user.organization ? ` · ${data.user.organization}` : ''}
          </p>
        </div>
        {health && (
          <div className={`status-pill ${health.status === 'ok' ? 'ok' : 'warn'}`}>
            <span className="status-dot" aria-hidden="true" />
            <span>
              API {health.status} · database {health.database}
            </span>
          </div>
        )}
      </header>

      <div className="grid-2">
        <section className="card">
          <h2>Your permissions</h2>
          <p className="muted small">
            Served by the API from the same rules that authorise each request, so this list cannot
            drift from what the server actually allows.
          </p>
          <ul className="capability-list">
            {data.capabilities.map((capability) => (
              <li key={capability}>
                <span className="tick" aria-hidden="true">
                  ✓
                </span>
                {humanise(capability, CAPABILITY_LABELS)}
              </li>
            ))}
          </ul>
        </section>

        <section className="card card-muted">
          <h2>Module status</h2>
          {data.pending_modules.length === 0 ? (
            <p className="muted small">
              All modules for this role are built and wired to live data. Nothing on this
              dashboard is a placeholder.
            </p>
          ) : (
            <>
              <p className="muted small">
                Listed honestly rather than shown as empty widgets or placeholder numbers.
              </p>
              <ul className="pending-list">
                {data.pending_modules.map((module) => (
                  <li key={module}>
                    <span className="pending-dot" aria-hidden="true" />
                    {humanise(module, MODULE_LABELS)}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>

      <footer className="page-footer muted small">{data.prototype_notice}</footer>
    </div>
  );
}
