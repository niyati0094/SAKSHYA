import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ApiError, apiFetch } from '../api/client';
import type { AttemptResult, ScenarioDetail } from '../types';

function ResultView({ result }: { result: AttemptResult }) {
  return (
    <div className="page">
      <nav className="breadcrumb">
        <Link to="/learner/simulations">Simulation lab</Link>
        <span aria-hidden="true">/</span>
        <span>{result.scenario_title}</span>
      </nav>

      <header className="page-header">
        <div>
          <p className="eyebrow">Result</p>
          <h1>{result.scenario_title}</h1>
        </div>
        <div className="big-figure" style={{ margin: 0 }}>
          {Math.round(result.percentage * 100)}%
          <span className="big-figure-caption">{result.band}</span>
        </div>
      </header>

      {result.evidence_id !== null && (
        <div className="alert alert-success" role="status">
          <strong>Evidence recorded.</strong> This attempt produced evidence #
          {result.evidence_id} against <code>{result.competency_code}</code>. Your competency
          profile has been recalculated —{' '}
          <Link to="/learner">see the updated level</Link>.
        </div>
      )}

      <section className="card why-card">
        <h2>How this was scored</h2>
        <ol className="why-list">
          {result.explanation.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ol>
        <p className="muted small why-note">{result.scoring_note}</p>
      </section>

      <section className="card">
        <h2>Decision by decision</h2>
        <ul className="outcome-list">
          {result.outcomes.map((outcome) => (
            <li
              key={outcome.decision_key}
              className={`outcome ${outcome.is_best ? 'outcome-best' : outcome.credit >= 0.5 ? 'outcome-partial' : 'outcome-weak'}`}
            >
              <div className="outcome-head">
                <strong>{outcome.prompt}</strong>
                <span className="outcome-credit">
                  {Math.round(outcome.credit * 100)}% · weight {outcome.weight}
                </span>
              </div>
              <p className="small">
                <em>You chose:</em>{' '}
                {outcome.chosen_text ?? <span className="muted">No decision recorded</span>}
              </p>
              <p className="small outcome-rationale">{outcome.rationale}</p>
              {!outcome.is_best && (
                <p className="small muted">
                  <strong>Stronger choice:</strong> {outcome.best_text}
                </p>
              )}
            </li>
          ))}
        </ul>
      </section>

      {result.debrief && (
        <section className="card card-muted">
          <h2>Debrief</h2>
          <p className="muted small">
            Narrative summary generated after scoring. It explains the result and cannot change
            it.
          </p>
          <pre className="debrief">{result.debrief}</pre>
        </section>
      )}
    </div>
  );
}

/** Read-only view of a previously completed attempt. */
export function SimulationAttemptPage() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await apiFetch<AttemptResult>(`/simulations/attempts/${attemptId}`);
        if (!cancelled) setResult(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : 'Unable to load this attempt.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [attemptId]);

  if (loading) {
    return (
      <div className="centered-state" role="status" aria-live="polite">
        <div className="spinner" aria-hidden="true" />
        <p>Loading your attempt…</p>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="page">
        <div className="alert alert-error" role="alert">
          {error ?? 'Unable to load this attempt.'}
        </div>
        <Link to="/learner/simulations" className="btn btn-ghost">
          Back to the simulation lab
        </Link>
      </div>
    );
  }

  return <ResultView result={result} />;
}

export function SimulationRunPage() {
  const { scenarioCode } = useParams<{ scenarioCode: string }>();
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await apiFetch<ScenarioDetail>(`/simulations/${scenarioCode}`);
        if (!cancelled) setScenario(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : 'Unable to load this scenario.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [scenarioCode]);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const data = await apiFetch<AttemptResult>(`/simulations/${scenarioCode}/submit`, {
        method: 'POST',
        body: JSON.stringify({ answers }),
      });
      setResult(data);
      window.scrollTo({ top: 0 });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not submit your attempt.');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="centered-state" role="status" aria-live="polite">
        <div className="spinner" aria-hidden="true" />
        <p>Loading the scenario…</p>
      </div>
    );
  }

  if (error && !scenario) {
    return (
      <div className="page">
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      </div>
    );
  }

  if (result) return <ResultView result={result} />;
  if (!scenario) return null;

  const answered = Object.keys(answers).length;
  const complete = answered === scenario.decisions.length;

  return (
    <div className="page">
      <nav className="breadcrumb">
        <Link to="/learner/simulations">Simulation lab</Link>
        <span aria-hidden="true">/</span>
        <span>{scenario.title}</span>
      </nav>

      <header className="page-header">
        <div>
          <p className="eyebrow">Simulation</p>
          <h1>{scenario.title}</h1>
        </div>
        <span className="status-pill">
          {answered} of {scenario.decisions.length} decided
        </span>
      </header>

      <section className="card briefing">
        <h2>Briefing</h2>
        <p>{scenario.briefing}</p>
      </section>

      {scenario.decisions.map((decision, index) => (
        <section key={decision.key} className="card">
          <h2>
            Decision {index + 1}. {decision.prompt}
          </h2>
          <p className="muted small">{decision.context}</p>

          <ul className="option-list" style={{ marginTop: '0.9rem' }}>
            {decision.options.map((option) => (
              <li key={option.key}>
                <label
                  className={`option-row ${answers[decision.key] === option.key ? 'option-chosen' : ''}`}
                >
                  <input
                    type="radio"
                    name={decision.key}
                    checked={answers[decision.key] === option.key}
                    onChange={() =>
                      setAnswers((current) => ({ ...current, [decision.key]: option.key }))
                    }
                  />
                  <span>{option.text}</span>
                </label>
              </li>
            ))}
          </ul>
        </section>
      ))}

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      <div className="submit-bar">
        {!complete && (
          <span className="muted small">
            Unanswered decisions score zero — leaving a judgement unmade counts against you.
          </span>
        )}
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void submit()}
          disabled={submitting || answered === 0}
        >
          {submitting ? 'Scoring…' : 'Submit attempt'}
        </button>
      </div>

      <footer className="page-footer muted small">{scenario.prototype_notice}</footer>
    </div>
  );
}
