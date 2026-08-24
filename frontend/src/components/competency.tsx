/** Shared presentation pieces for competency data. */

import type { CompetencyResult, CompetencyStatus } from '../types';

export const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  simulation: 'Simulation',
  practical_submission: 'Practical submission',
  sme_verified: 'Expert verified',
  assessment: 'Assessment',
  peer_review: 'Peer review',
  course_completion: 'Course completion',
};

export const STATUS_LABELS: Record<CompetencyStatus, string> = {
  established: 'Established',
  insufficient_evidence: 'Insufficient evidence',
  no_evidence: 'No evidence',
};

export function evidenceTypeLabel(value: string): string {
  return EVIDENCE_TYPE_LABELS[value] ?? value.replace(/_/g, ' ');
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function StatusBadge({ status }: { status: CompetencyStatus }) {
  return <span className={`status-badge status-${status}`}>{STATUS_LABELS[status]}</span>;
}

export function CriticalityBadge({ criticality }: { criticality: string }) {
  return <span className={`crit-badge crit-${criticality}`}>{criticality}</span>;
}

/**
 * Mastery bar with the role's required level marked on the scale, so "how far
 * from target" is legible at a glance rather than needing arithmetic.
 */
export function MasteryBar({
  result,
  targetLevel,
}: {
  result: CompetencyResult;
  targetLevel?: number | null;
}) {
  // Level band lower bounds, mirroring engines/constants.LEVEL_BANDS.
  const bands: Record<number, number> = { 1: 0, 2: 0.4, 3: 0.6, 4: 0.8 };
  const targetPct = targetLevel ? bands[targetLevel] * 100 : null;
  const asserted = result.status === 'established';
  const masteryPct = (result.mastery ?? 0) * 100;

  return (
    <div className="mastery">
      <div
        className="mastery-track"
        role="img"
        aria-label={
          result.mastery === null
            ? 'No mastery estimate — no evidence recorded'
            : `Mastery ${(result.mastery * 100).toFixed(0)} percent` +
              (targetLevel ? `, target level ${targetLevel}` : '')
        }
      >
        <div
          className={`mastery-fill ${asserted ? '' : 'mastery-fill-unasserted'}`}
          style={{ width: `${masteryPct}%` }}
        />
        {targetPct !== null && (
          <div className="mastery-target" style={{ left: `${targetPct}%` }} title="Required level" />
        )}
      </div>
      <div className="mastery-scale" aria-hidden="true">
        <span>Awareness</span>
        <span>Working</span>
        <span>Proficient</span>
        <span>Expert</span>
      </div>
    </div>
  );
}

/** Small horizontal meter used for confidence and its components. */
export function Meter({ value, label }: { value: number; label?: string }) {
  const pct = Math.round(value * 100);
  const tone = value >= 0.7 ? 'high' : value >= 0.4 ? 'mid' : 'low';

  return (
    <div className="meter-row">
      {label && <span className="meter-label">{label}</span>}
      <div className="meter-track">
        <div className={`meter-fill meter-${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="meter-value">{pct}%</span>
    </div>
  );
}
