import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, apiFetch } from '../api/client';
import type { Pathway, Recommendation } from '../types';

const STAGE_LABELS: Record<string, string> = {
  learn: 'Learn',
  practice: 'Practice',
  prove: 'Prove',
};

const STAGE_BLURB: Record<string, string> = {
  learn: 'Build the underlying understanding first.',
  practice: 'Apply it — reading about it is not evidence.',
  prove: 'Demonstrate it and generate strong evidence.',
};

function StageChain({ active }: { active: string }) {
  return (
    <ol className="stage-chain" aria-label="Learn, Practice, Prove progression">
      {(['learn', 'practice', 'prove'] as const).map((stage) => (
        <li key={stage} className={stage === active ? 'stage-active' : ''}>
          {STAGE_LABELS[stage]}
        </li>
      ))}
    </ol>
  );
}

function RecommendationCard({ item }: { item: Recommendation }) {
  const isSimulation = item.resource.is_interactive;

  return (
    <article className={`card rec-card sev-${item.severity_band}`}>
      <header className="rec-head">
        <div className="rec-rank" aria-hidden="true">
          {item.rank}
        </div>
        <div className="rec-title">
          <h3>{item.resource.title}</h3>
          <p className="muted small">
            {item.competency_name} · {item.resource.estimated_minutes} min ·{' '}
            {item.resource.provider}
          </p>
        </div>
        <span className={`sev-badge sev-${item.severity_band}`}>{item.severity_band}</span>
      </header>

      <StageChain active={item.stage} />
      <p className="small muted">{STAGE_BLURB[item.stage]}</p>

      <p className="small">{item.resource.description}</p>

      {/* The explainability requirement: why this, why now. */}
      <div className="why-box">
        <strong className="small">Recommended because</strong>
        <ul className="why-bullets">
          {item.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </div>

      {item.blocked && (
        <div className="alert alert-warn small" role="note">
          Prerequisite not yet established: {item.unmet_prerequisites.join(', ')}
        </div>
      )}

      <footer className="competency-card-foot">
        <span className="muted small">
          Targets level {item.resource.target_level} · {item.resource.competency_code}
        </span>
        {isSimulation ? (
          <Link
            className="btn btn-primary"
            to={`/learner/simulations/${item.resource.external_id}`}
          >
            Start simulation
          </Link>
        ) : (
          <span className="muted small resource-note">Prototype catalogue resource</span>
        )}
      </footer>
    </article>
  );
}

export function PathwayPage() {
  const [data, setData] = useState<Pathway | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const result = await apiFetch<Pathway>('/me/pathway');
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : 'Unable to load your pathway.');
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
        <p>Calculating your gaps and pathway…</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page">
        <div className="alert alert-error" role="alert">
          {error ?? 'Unable to load your pathway.'}
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Personalised pathway</p>
          <h1>What to do next</h1>
          <p className="muted">
            Ranked by gap severity, staged Learn → Practice → Prove. Every recommendation
            states the reasoning that selected it.
          </p>
        </div>
      </header>

      {data.gaps.length === 0 ? (
        <div className="card">
          <p className="empty-note">
            No competency gaps detected against your role. Complete a simulation to keep your
            evidence current.
          </p>
        </div>
      ) : (
        <>
          <section className="card">
            <h2>Competency gaps</h2>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th scope="col">Competency</th>
                    <th scope="col">Current</th>
                    <th scope="col">Target</th>
                    <th scope="col">Gap</th>
                    <th scope="col">Confidence</th>
                    <th scope="col">Criticality</th>
                    <th scope="col">Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {data.gaps.map((gap) => (
                    <tr key={gap.competency_code}>
                      <th scope="row">
                        <Link to={`/learner/competency/${gap.competency_id}`}>
                          <span className="cell-title">{gap.competency_name}</span>
                        </Link>
                        {gap.evidence_limited && (
                          <span className="cell-sub">Limited by evidence, not by score</span>
                        )}
                      </th>
                      <td>{gap.status === 'established' ? gap.current_level : '—'}</td>
                      <td>{gap.target_level}</td>
                      <td>{gap.level_shortfall}</td>
                      <td>{gap.confidence.toFixed(2)}</td>
                      <td>
                        <span className={`crit-badge crit-${gap.criticality}`}>
                          {gap.criticality}
                        </span>
                      </td>
                      <td>
                        <span className={`sev-badge sev-${gap.severity_band}`}>
                          {gap.severity.toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <h2 className="section-heading">Recommended next steps</h2>
          <div className="rec-list">
            {data.recommendations.map((item) => (
              <RecommendationCard key={item.resource.external_id} item={item} />
            ))}
          </div>
        </>
      )}

      <footer className="page-footer muted small">
        <p>{data.method_note}</p>
        <p style={{ marginTop: '0.5rem' }}>{data.catalog.notice}</p>
      </footer>
    </div>
  );
}
