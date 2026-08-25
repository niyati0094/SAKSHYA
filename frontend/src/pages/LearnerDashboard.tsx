import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, apiFetch } from '../api/client';
import { CriticalityBadge, MasteryBar, Meter, StatusBadge } from '../components/competency';
import type {
  CompetencyProfile,
  CompetencyProfileEntry,
  Pathway,
  Recommendation,
} from '../types';

function CompetencyCard({ entry }: { entry: CompetencyProfileEntry }) {
  const { competency, result, target_level, target_level_label, criticality } = entry;
  const asserted = result.status === 'established';

  return (
    <article className={`card competency-card ${entry.meets_target ? '' : 'below-target'}`}>
      <header className="competency-card-head">
        <div>
          <h3>{competency.name}</h3>
          {competency.domain && <p className="muted small">{competency.domain}</p>}
        </div>
        <StatusBadge status={result.status} />
      </header>

      <div className="level-row">
        <div className="level-current">
          <span className="level-value">{asserted ? result.level : '—'}</span>
          <span className="level-caption">
            {asserted ? result.level_label : 'Not established'}
          </span>
        </div>
        <span className="level-arrow" aria-hidden="true">
          →
        </span>
        <div className="level-target">
          <span className="level-value">{target_level}</span>
          <span className="level-caption">{target_level_label} required</span>
        </div>
        <CriticalityBadge criticality={criticality} />
      </div>

      <MasteryBar result={result} targetLevel={target_level} />

      <Meter value={result.confidence} label="Confidence" />

      <footer className="competency-card-foot">
        <span className="muted small">
          {result.counted_evidence_count} counted
          {result.evidence_count !== result.counted_evidence_count &&
            ` · ${result.evidence_count - result.counted_evidence_count} excluded`}
        </span>
        <Link className="why-link" to={`/learner/competency/${competency.id}`}>
          Why this level?
        </Link>
      </footer>
    </article>
  );
}

/**
 * The demo spine in one card: the most severe gap, why it is the most severe,
 * and the single next action. Everything here comes from the deterministic
 * pathway endpoint.
 */
function TopPriority({ recommendation }: { recommendation: Recommendation }) {
  const isSimulation = recommendation.resource.is_interactive;

  return (
    <section className={`card priority-card sev-${recommendation.severity_band}`}>
      <div className="priority-head">
        <span className={`sev-badge sev-${recommendation.severity_band}`}>
          {recommendation.severity_band} priority
        </span>
        <span className="muted small">Highest-severity gap for your role</span>
      </div>

      <h2>{recommendation.competency_name}</h2>

      <ul className="why-bullets">
        {recommendation.reasons.slice(0, 3).map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>

      <div className="priority-actions">
        {isSimulation ? (
          <Link
            className="btn btn-primary"
            to={`/learner/simulations/${recommendation.resource.external_id}`}
          >
            {recommendation.resource.title}
          </Link>
        ) : (
          <span className="muted small">Next step: {recommendation.resource.title}</span>
        )}
        <Link className="btn btn-ghost" to="/learner/pathway">
          See full pathway
        </Link>
      </div>
    </section>
  );
}

export function LearnerDashboard() {
  const [profile, setProfile] = useState<CompetencyProfile | null>(null);
  const [priority, setPriority] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [data, pathway] = await Promise.all([
          apiFetch<CompetencyProfile>('/me/competency-profile'),
          // The pathway is advisory here: if it fails, the profile still renders.
          apiFetch<Pathway>('/me/pathway?limit=1').catch(() => null),
        ]);
        if (cancelled) return;
        setProfile(data);
        setPriority(pathway?.recommendations[0] ?? null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : 'Unable to load your profile.');
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
        <p>Recalculating your competency profile from evidence…</p>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="page">
        <div className="alert alert-error" role="alert">
          {error ?? 'Unable to load your profile.'}
        </div>
      </div>
    );
  }

  if (!profile.role) {
    return (
      <div className="page">
        <div className="card">
          <h2>No statistical role assigned</h2>
          <p className="muted">
            Competencies are assessed against a role. Once a role is assigned, your competency
            profile will appear here.
          </p>
        </div>
      </div>
    );
  }

  const { summary } = profile;

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Competency profile</p>
          <h1>{profile.role.name}</h1>
          <p className="muted">
            Every level below is recalculated from your evidence ledger on each visit — no score
            is stored.
          </p>
        </div>
      </header>

      {priority && <TopPriority recommendation={priority} />}

      <section className="stat-row">
        <div className="stat">
          <span className="stat-value">{summary.total_competencies}</span>
          <span className="stat-label">Competencies in role</span>
        </div>
        <div className="stat stat-ok">
          <span className="stat-value">{summary.meeting_target}</span>
          <span className="stat-label">Meeting target</span>
        </div>
        <div className="stat stat-warn">
          <span className="stat-value">{summary.below_target}</span>
          <span className="stat-label">Below target</span>
        </div>
        <div className="stat">
          <span className="stat-value">{summary.insufficient_evidence}</span>
          <span className="stat-label">Insufficient evidence</span>
        </div>
        <div className="stat">
          <span className="stat-value">{summary.total_counted_evidence}</span>
          <span className="stat-label">Evidence items counted</span>
        </div>
      </section>

      <div className="competency-grid">
        {profile.competencies.map((entry) => (
          <CompetencyCard key={entry.competency.id} entry={entry} />
        ))}
      </div>

      <footer className="page-footer muted small">{profile.prototype_notice}</footer>
    </div>
  );
}
