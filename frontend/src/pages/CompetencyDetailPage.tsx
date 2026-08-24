import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ApiError, apiFetch } from '../api/client';
import {
  MasteryBar,
  Meter,
  StatusBadge,
  evidenceTypeLabel,
  formatDate,
} from '../components/competency';
import type { CompetencyDetail } from '../types';

const COMPONENT_HELP: Record<string, string> = {
  volume: 'How much effective evidence exists',
  diversity: 'How many distinct kinds of evidence',
  recency: 'How recent the strongest evidence is',
  agreement: 'How consistent the evidence is with itself',
};

export function CompetencyDetailPage() {
  const { competencyId } = useParams<{ competencyId: string }>();
  const [detail, setDetail] = useState<CompetencyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showMethod, setShowMethod] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    async function load() {
      try {
        const data = await apiFetch<CompetencyDetail>(`/me/competencies/${competencyId}`);
        if (!cancelled) setDetail(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : 'Unable to load this competency.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [competencyId]);

  if (loading) {
    return (
      <div className="centered-state" role="status" aria-live="polite">
        <div className="spinner" aria-hidden="true" />
        <p>Loading the evidence trail…</p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="page">
        <div className="alert alert-error" role="alert">
          {error ?? 'Unable to load this competency.'}
        </div>
        <Link to="/learner" className="btn btn-ghost">
          Back to profile
        </Link>
      </div>
    );
  }

  const { result, competency, method } = detail;
  const breakdown = result.confidence_breakdown;

  return (
    <div className="page">
      <nav className="breadcrumb">
        <Link to="/learner">Competency profile</Link>
        <span aria-hidden="true">/</span>
        <span>{competency.name}</span>
      </nav>

      <header className="page-header">
        <div>
          <p className="eyebrow">Evidence explorer</p>
          <h1>{competency.name}</h1>
          {competency.description && <p className="muted detail-desc">{competency.description}</p>}
        </div>
        <StatusBadge status={result.status} />
      </header>

      {/* The headline answer */}
      <section className="card why-card">
        <h2>Why does SAKSHYA believe this?</h2>
        <ol className="why-list">
          {result.explanation.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ol>
        <p className="muted small why-note">
          Generated from the same arithmetic that produced the result — not written by a language
          model.
        </p>
      </section>

      <div className="grid-2">
        <section className="card">
          <h2>Mastery</h2>
          <div className="big-figure">
            {result.mastery === null ? '—' : result.mastery.toFixed(2)}
            <span className="big-figure-caption">
              {result.status === 'established'
                ? `Level ${result.level} · ${result.level_label}`
                : 'No level asserted'}
            </span>
          </div>
          <MasteryBar result={result} targetLevel={detail.target_level} />
          {detail.target_level && (
            <p className="muted small">
              Required for this role: level {detail.target_level} ({detail.target_level_label})
              {detail.meets_target === false && ' — currently below target'}
            </p>
          )}
        </section>

        <section className="card">
          <h2>Confidence</h2>
          <div className="big-figure">
            {result.confidence.toFixed(2)}
            <span className="big-figure-caption">
              {breakdown ? `Limited by ${breakdown.limiting_factor}` : 'No evidence to assess'}
            </span>
          </div>
          {breakdown ? (
            <div className="component-list">
              {(['volume', 'diversity', 'recency', 'agreement'] as const).map((key) => (
                <div key={key} className="component">
                  <div className="component-head">
                    <strong>{key}</strong>
                    <span className="muted small">{COMPONENT_HELP[key]}</span>
                  </div>
                  <Meter value={breakdown[key]} />
                </div>
              ))}
            </div>
          ) : (
            <p className="muted small">
              Confidence cannot be assessed without accepted evidence.
            </p>
          )}
        </section>
      </div>

      {/* The audit trail */}
      <section className="card">
        <h2>How each evidence item contributed</h2>
        <p className="muted small">
          Multiply each score by its share and add them together to reproduce the mastery figure.
        </p>

        {detail.contributions.length === 0 ? (
          <p className="empty-note">
            No evidence has been recorded for this competency yet.
          </p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Evidence</th>
                  <th scope="col">Score</th>
                  <th scope="col">Type weight</th>
                  <th scope="col">Recency</th>
                  <th scope="col">Effective</th>
                  <th scope="col">Share</th>
                </tr>
              </thead>
              <tbody>
                {detail.contributions.map((c) => {
                  const source = detail.evidence.find((e) => e.id === c.evidence_id);
                  return (
                    <tr key={c.evidence_id} className={c.counted ? '' : 'row-excluded'}>
                      <th scope="row">
                        <span className="cell-title">
                          {source?.activity_title ?? `Evidence #${c.evidence_id}`}
                        </span>
                        <span className="cell-sub">
                          {evidenceTypeLabel(c.evidence_type)}
                          {source && ` · ${formatDate(source.observed_at)}`}
                        </span>
                        {!c.counted && (
                          <span className="excluded-flag">Excluded — {c.excluded_reason}</span>
                        )}
                      </th>
                      <td>{c.score.toFixed(2)}</td>
                      <td>{c.type_weight.toFixed(1)}</td>
                      <td>{c.recency_factor.toFixed(2)}</td>
                      <td>{c.effective_weight.toFixed(2)}</td>
                      <td>
                        {c.counted ? `${(c.contribution_share * 100).toFixed(0)}%` : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* The rules themselves */}
      <section className="card card-muted">
        <button
          type="button"
          className="disclosure"
          aria-expanded={showMethod}
          onClick={() => setShowMethod((open) => !open)}
        >
          <span aria-hidden="true">{showMethod ? '▾' : '▸'}</span>
          How this is calculated
        </button>

        {showMethod && (
          <div className="method-body">
            <p className="small">{method.summary}</p>
            <p className="small muted">{method.weighting_rationale}</p>

            <h3>Evidence type weights</h3>
            <ul className="weight-list">
              {Object.entries(method.evidence_type_weights)
                .sort((a, b) => b[1] - a[1])
                .map(([type, weight]) => (
                  <li key={type}>
                    <span>{evidenceTypeLabel(type)}</span>
                    <span className="weight-value">×{weight.toFixed(1)}</span>
                  </li>
                ))}
            </ul>

            <p className="small muted">
              Evidence loses half its influence every {method.recency.half_life_days} days. A
              competency needs at least {method.sufficiency_thresholds.min_effective_evidence}{' '}
              effective evidence weight and {method.sufficiency_thresholds.min_confidence}{' '}
              confidence before any level is asserted.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
