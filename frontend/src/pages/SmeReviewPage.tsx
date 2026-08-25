import { useCallback, useEffect, useMemo, useState } from 'react';
import { ApiError, apiFetch } from '../api/client';
import { GateBench } from '../components/GateBench';
import type { GeneratedQuestion, ReviewSummary } from '../types';

type Filter = 'pending' | 'approved' | 'rejected' | 'all';

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'pending', label: 'Awaiting review' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'all', label: 'All' },
];

function QuestionCard({
  question,
  onReviewed,
}: {
  question: GeneratedQuestion;
  onReviewed: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [stem, setStem] = useState(question.stem);
  const [options, setOptions] = useState<string[]>(question.options);
  const [correctIndex, setCorrectIndex] = useState(question.correct_index);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const dirty =
    stem !== question.stem ||
    correctIndex !== question.correct_index ||
    options.some((option, index) => option !== question.options[index]);

  async function submit(decision: 'approved' | 'rejected') {
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/questions/${question.id}/review`, {
        method: 'POST',
        body: JSON.stringify({
          decision,
          note: note.trim() || null,
          ...(dirty ? { stem, options, correct_index: correctIndex } : {}),
        }),
      });
      onReviewed();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save your decision.');
    } finally {
      setBusy(false);
    }
  }

  const { citation } = question;

  return (
    <article className={`card question-card review-${question.review_status}`}>
      <header className="question-head">
        <div className="question-flags">
          <span className={`review-badge review-${question.review_status}`}>
            {question.review_status}
          </span>
          <span
            className={`ground-badge ground-${question.grounding_status}`}
            title={question.grounding_note ?? 'Passed all five verification gates'}
          >
            {question.grounding_status === 'grounded'
              ? '✓ Passed 5 gates'
              : `✗ ${question.failed_gate} ${question.failed_gate_name}`}
          </span>
          {question.competency_name ? (
            <span className="tag-badge">{question.competency_name}</span>
          ) : (
            <span className="tag-badge tag-none">Untagged</span>
          )}
          {question.edited && <span className="tag-badge">Edited</span>}
        </div>
        <span className="muted small">{question.generation_strategy}</span>
      </header>

      {editing ? (
        <label className="field">
          <span>Question</span>
          <textarea rows={3} value={stem} onChange={(e) => setStem(e.target.value)} />
        </label>
      ) : (
        <h3 className="question-stem">{question.stem}</h3>
      )}

      <ol className="option-list">
        {options.map((option, index) => (
          <li key={index} className={index === correctIndex ? 'option-correct' : ''}>
            <label className="option-row">
              <input
                type="radio"
                name={`correct-${question.id}`}
                checked={index === correctIndex}
                disabled={!editing}
                onChange={() => setCorrectIndex(index)}
              />
              {editing ? (
                <input
                  type="text"
                  value={option}
                  onChange={(e) =>
                    setOptions(options.map((o, i) => (i === index ? e.target.value : o)))
                  }
                />
              ) : (
                <span>{option}</span>
              )}
            </label>
          </li>
        ))}
      </ol>

      {/* The citation is the point: it names a stored passage, not a guess. */}
      <div className="citation-box">
        <div className="citation-head">
          <strong>Source</strong>
          <span className="muted small">
            {citation.document_title}
            {citation.section_title && ` · ${citation.section_title}`}
            {citation.page_number !== null && ` · p.${citation.page_number}`}
          </span>
        </div>
        <blockquote>“{citation.quote}”</blockquote>
        <p className="muted small">
          Verified against passage #{citation.chunk_id} · grounding score{' '}
          {question.grounding_score.toFixed(2)}
        </p>
      </div>

      {question.grounding_note && (
        <div className="alert alert-warn small" role="alert">
          {question.grounding_note}
        </div>
      )}

      {error && (
        <div className="alert alert-error small" role="alert">
          {error}
        </div>
      )}

      <div className="review-actions">
        <input
          type="text"
          className="review-note"
          placeholder="Reviewer note (optional)"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => setEditing((open) => !open)}
          disabled={busy}
        >
          {editing ? 'Done editing' : 'Edit'}
        </button>
        <button
          type="button"
          className="btn btn-danger"
          onClick={() => void submit('rejected')}
          disabled={busy}
        >
          Reject
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void submit('approved')}
          disabled={busy}
        >
          {dirty ? 'Save & approve' : 'Approve'}
        </button>
      </div>

      {dirty && (
        <p className="muted small">
          Edits are re-verified against the cited passage before the decision is stored.
        </p>
      )}
    </article>
  );
}

export function SmeReviewPage() {
  const [questions, setQuestions] = useState<GeneratedQuestion[] | null>(null);
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [filter, setFilter] = useState<Filter>('pending');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [items, counts] = await Promise.all([
        apiFetch<GeneratedQuestion[]>('/questions'),
        apiFetch<ReviewSummary>('/questions/summary'),
      ]);
      setQuestions(items);
      setSummary(counts);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to load the review queue.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const visible = useMemo(
    () =>
      (questions ?? []).filter((q) => filter === 'all' || q.review_status === filter),
    [questions, filter],
  );

  if (loading) {
    return (
      <div className="centered-state" role="status" aria-live="polite">
        <div className="spinner" aria-hidden="true" />
        <p>Loading the review queue…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Subject matter expert</p>
          <h1>Question review queue</h1>
          <p className="muted">
            Every generated question cites a stored passage and is verified against it before
            reaching you. Nothing is published to learners without your approval.
          </p>
        </div>
      </header>

      {summary && (
        <section className="stat-row">
          <div className="stat">
            <span className="stat-value">{summary.total}</span>
            <span className="stat-label">Generated</span>
          </div>
          <div className="stat stat-warn">
            <span className="stat-value">{summary.pending}</span>
            <span className="stat-label">Awaiting review</span>
          </div>
          <div className="stat stat-ok">
            <span className="stat-value">{summary.approved}</span>
            <span className="stat-label">Approved</span>
          </div>
          <div className="stat">
            <span className="stat-value">{summary.rejected}</span>
            <span className="stat-label">Rejected</span>
          </div>
          <div className="stat stat-danger">
            <span className="stat-value">{Math.round(summary.rejection_rate * 100)}%</span>
            <span className="stat-label">Rejected by a gate</span>
          </div>
          <div className="stat">
            <span className="stat-value">{summary.untagged}</span>
            <span className="stat-label">Untagged</span>
          </div>
        </section>
      )}

      {summary && (
        <section className="card gate-card">
          <h2>Verification gates</h2>
          <p className="muted small">
            Every generated item passes five gates before it can reach a learner. The
            rejection rate is published, not hidden — a pipeline that never rejects
            anything is not verifying anything.
          </p>
          <ul className="gate-list">
            {Object.entries(summary.gate_names).map(([gate, name]) => {
              const count = summary.rejections_by_gate[gate] ?? 0;
              return (
                <li key={gate} className={count > 0 ? 'gate-fired' : ''}>
                  <span className="gate-code">{gate}</span>
                  <span className="gate-name">{name}</span>
                  <span className="gate-count">
                    {count > 0 ? `${count} rejected` : 'none rejected'}
                  </span>
                </li>
              );
            })}
          </ul>
          <p className="muted small gate-note">
            <strong>G3 Anchor preservation</strong> is the statistics-specific gate: it
            rejects a question that drops the population, reference period, unit or
            denominator its source claim depends on. A definition without its context is
            not incomplete — it is wrong.
          </p>
        </section>
      )}

      <GateBench />

      <div className="filter-row" role="group" aria-label="Filter questions">
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
            {filter === 'pending'
              ? 'Nothing is waiting for review. Generated questions appear here automatically.'
              : 'No questions match this filter.'}
          </p>
        </div>
      ) : (
        <div className="question-list">
          {visible.map((question) => (
            <QuestionCard key={question.id} question={question} onReviewed={load} />
          ))}
        </div>
      )}
    </div>
  );
}
