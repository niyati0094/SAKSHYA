import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, apiFetch } from '../api/client';
import { formatDate } from '../components/competency';
import type { ScenarioSummary, SimulationAttemptSummary } from '../types';

export function SimulationsPage() {
  const [scenarios, setScenarios] = useState<ScenarioSummary[] | null>(null);
  const [attempts, setAttempts] = useState<SimulationAttemptSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [list, mine] = await Promise.all([
          apiFetch<ScenarioSummary[]>('/simulations'),
          apiFetch<SimulationAttemptSummary[]>('/simulations/attempts/mine'),
        ]);
        if (cancelled) return;
        setScenarios(list);
        setAttempts(mine);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : 'Unable to load simulations.');
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
        <p>Loading the simulation lab…</p>
      </div>
    );
  }

  if (error || !scenarios) {
    return (
      <div className="page">
        <div className="alert alert-error" role="alert">
          {error ?? 'Unable to load simulations.'}
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Simulation lab</p>
          <h1>Prove it in practice</h1>
          <p className="muted">
            Make the decisions a statistical officer actually faces. Each scenario is scored
            against an expert-written rubric and produces evidence in your ledger — the
            strongest evidence type SAKSHYA recognises.
          </p>
        </div>
      </header>

      <div className="competency-grid">
        {scenarios.map((scenario) => {
          const previous = attempts.filter((a) => a.scenario_code === scenario.code);
          const best = previous.length
            ? Math.max(...previous.map((a) => a.percentage))
            : null;

          return (
            <article key={scenario.code} className="card competency-card">
              <header className="competency-card-head">
                <div>
                  <h3>{scenario.title}</h3>
                  <p className="muted small">
                    {scenario.decision_count} decisions · ~{scenario.estimated_minutes} min
                  </p>
                </div>
                {best !== null && (
                  <span className="status-badge status-established">
                    Best {Math.round(best * 100)}%
                  </span>
                )}
              </header>

              <p className="small">{scenario.summary}</p>

              <footer className="competency-card-foot">
                <span className="muted small">
                  {previous.length
                    ? `${previous.length} attempt${previous.length === 1 ? '' : 's'}`
                    : 'Not yet attempted'}
                </span>
                <Link className="btn btn-primary" to={`/learner/simulations/${scenario.code}`}>
                  {previous.length ? 'Run again' : 'Start'}
                </Link>
              </footer>
            </article>
          );
        })}
      </div>

      {attempts.length > 0 && (
        <section className="card">
          <h2>Your attempts</h2>
          <ul className="evidence-list" style={{ marginTop: '0.9rem' }}>
            {attempts.map((attempt) => (
              <li key={attempt.id} className="attempt-row">
                <div>
                  <Link to={`/learner/simulations/attempts/${attempt.id}`}>
                    {attempt.scenario_title}
                  </Link>
                  <p className="muted small">{formatDate(attempt.completed_at)}</p>
                </div>
                <div className="evidence-score">
                  <span className="evidence-score-value">
                    {Math.round(attempt.percentage * 100)}%
                  </span>
                  <span className="muted small">{attempt.band}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
