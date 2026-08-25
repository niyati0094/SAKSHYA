import { useEffect, useState } from 'react';
import { ApiError, apiFetch } from '../api/client';
import type { OrganisationOverview } from '../types';

export function AdminDashboard() {
  const [data, setData] = useState<OrganisationOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const result = await apiFetch<OrganisationOverview>('/admin/overview');
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : 'Unable to load the overview.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="centered-state" role="status" aria-live="polite">
        <div className="spinner" aria-hidden="true" />
        <p>Aggregating competency data across the cohort…</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page">
        <div className="alert alert-error" role="alert">
          {error ?? 'Unable to load the overview.'}
        </div>
      </div>
    );
  }

  const maxGap = Math.max(1, ...data.training_needs.map((n) => n.learners_with_gap));

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Administrator</p>
          <h1>Organisation capacity overview</h1>
          <p className="muted">
            Aggregated from the same deterministic engine that produces each learner's profile,
            so these totals cannot disagree with the individual records behind them.
          </p>
        </div>
      </header>

      <section className="stat-row">
        <div className="stat">
          <span className="stat-value">{data.learner_count}</span>
          <span className="stat-label">Learners</span>
        </div>
        <div className="stat">
          <span className="stat-value">{data.learners_with_profile}</span>
          <span className="stat-label">With a role assigned</span>
        </div>
        <div className="stat stat-warn">
          <span className="stat-value">{data.total_gaps}</span>
          <span className="stat-label">Competency gaps</span>
        </div>
        <div className="stat stat-danger">
          <span className="stat-value">{data.urgent_gaps}</span>
          <span className="stat-label">Urgent gaps</span>
        </div>
      </section>

      <div className="grid-2">
        <section className="card">
          <h2>Role distribution</h2>
          {data.role_distribution.length === 0 ? (
            <p className="empty-note">No roles assigned yet.</p>
          ) : (
            <ul className="capability-list">
              {data.role_distribution.map((role) => (
                <li key={role.role_name}>
                  <span className="tick" aria-hidden="true">
                    ●
                  </span>
                  {role.role_name} — {role.learner_count}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card card-muted">
          <h2>How to read this</h2>
          <p className="small muted">
            A competency counts as a gap when the learner is below the level their role
            requires — <em>or</em> when there is not enough evidence to assert a level at all.
            The second case is shown separately as “unproven”, because it is a different
            problem: not a low score, but nothing to score.
          </p>
        </section>
      </div>

      <section className="card">
        <h2>Training needs</h2>
        <p className="muted small">
          Ranked by how many learners are affected, then by average severity.
        </p>

        {data.training_needs.length === 0 ? (
          <p className="empty-note">No competency gaps detected across the cohort.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Competency</th>
                  <th scope="col">Criticality</th>
                  <th scope="col">Target</th>
                  <th scope="col">Learners affected</th>
                  <th scope="col">Unproven</th>
                  <th scope="col">Avg severity</th>
                </tr>
              </thead>
              <tbody>
                {data.training_needs.map((need) => (
                  <tr key={need.competency_code}>
                    <th scope="row">
                      <span className="cell-title">{need.competency_name}</span>
                      <span className="cell-sub">{need.competency_code}</span>
                    </th>
                    <td>
                      <span className={`crit-badge crit-${need.criticality}`}>
                        {need.criticality}
                      </span>
                    </td>
                    <td>{need.target_level}</td>
                    <td>
                      <div className="bar-cell">
                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{
                              width: `${(need.learners_with_gap / maxGap) * 100}%`,
                            }}
                          />
                        </div>
                        <span>
                          {need.learners_with_gap} ({Math.round(need.share_of_learners * 100)}%)
                        </span>
                      </div>
                    </td>
                    <td>{need.learners_unproven}</td>
                    <td>{need.average_severity.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <footer className="page-footer muted small">{data.notice}</footer>
    </div>
  );
}
