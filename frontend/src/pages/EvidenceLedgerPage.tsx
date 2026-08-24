import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, apiFetch } from '../api/client';
import { evidenceTypeLabel, formatDate } from '../components/competency';
import type { EvidenceRecord } from '../types';

type Filter = 'all' | 'accepted' | 'pending' | 'rejected';

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'accepted', label: 'Counted' },
  { value: 'pending', label: 'Awaiting review' },
  { value: 'rejected', label: 'Rejected' },
];

export function EvidenceLedgerPage() {
  const [evidence, setEvidence] = useState<EvidenceRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>('all');

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await apiFetch<EvidenceRecord[]>('/me/evidence');
        if (!cancelled) setEvidence(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : 'Unable to load your evidence.');
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

  const visible = useMemo(
    () =>
      (evidence ?? []).filter((item) => filter === 'all' || item.review_status === filter),
    [evidence, filter],
  );

  if (loading) {
    return (
      <div className="centered-state" role="status" aria-live="polite">
        <div className="spinner" aria-hidden="true" />
        <p>Loading your evidence ledger…</p>
      </div>
    );
  }

  if (error || !evidence) {
    return (
      <div className="page">
        <div className="alert alert-error" role="alert">
          {error ?? 'Unable to load your evidence.'}
        </div>
      </div>
    );
  }

  const countedTotal = evidence.filter((item) => item.review_status === 'accepted').length;

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Evidence ledger</p>
          <h1>Your evidence trail</h1>
          <p className="muted">
            {evidence.length} record{evidence.length === 1 ? '' : 's'}, of which {countedTotal}{' '}
            currently count towards a competency estimate. Nothing is deleted — rejected and
            unreviewed evidence stays visible as part of the audit trail.
          </p>
        </div>
      </header>

      <div className="filter-row" role="group" aria-label="Filter evidence by review status">
        {FILTERS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`filter-chip ${filter === option.value ? 'active' : ''}`}
            aria-pressed={filter === option.value}
            onClick={() => setFilter(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <div className="card">
          <p className="empty-note">
            {evidence.length === 0
              ? 'No evidence has been recorded yet. Complete an assessment or simulation to generate your first evidence.'
              : 'No evidence matches this filter.'}
          </p>
        </div>
      ) : (
        <ul className="evidence-list">
          {visible.map((item) => (
            <li key={item.id} className={`card evidence-item status-${item.review_status}`}>
              <div className="evidence-main">
                <div className="evidence-head">
                  <h3>{item.activity_title}</h3>
                  <span className={`review-badge review-${item.review_status}`}>
                    {item.review_status === 'accepted'
                      ? 'Counted'
                      : item.review_status === 'pending'
                        ? 'Awaiting review'
                        : 'Rejected'}
                  </span>
                </div>

                <p className="muted small">
                  <Link to={`/learner/competency/${item.competency_id}`}>
                    {item.competency_name}
                  </Link>
                  {' · '}
                  {evidenceTypeLabel(item.evidence_type)}
                  {' · '}
                  {formatDate(item.observed_at)}
                  {item.source && ` · ${item.source}`}
                </p>

                {item.notes && <p className="evidence-note small">{item.notes}</p>}
                {item.reviewed_by && (
                  <p className="muted small">Reviewed by {item.reviewed_by}</p>
                )}
              </div>

              <div className="evidence-score">
                <span className="evidence-score-value">
                  {Math.round(item.normalized_score * 100)}%
                </span>
                <span className="muted small">
                  {item.raw_score} / {item.max_score}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
