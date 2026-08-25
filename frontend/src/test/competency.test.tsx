import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MasteryBar, Meter, StatusBadge, evidenceTypeLabel } from '../components/competency';
import type { CompetencyResult } from '../types';

function result(overrides: Partial<CompetencyResult> = {}): CompetencyResult {
  return {
    competency_id: 1,
    status: 'established',
    mastery: 0.71,
    level: 3,
    level_label: 'Proficient',
    confidence: 0.79,
    confidence_breakdown: null,
    evidence_count: 2,
    counted_evidence_count: 2,
    effective_evidence: 2.16,
    explanation: [],
    ...overrides,
  };
}

describe('StatusBadge', () => {
  it('names insufficient evidence explicitly rather than showing a level', () => {
    render(<StatusBadge status="insufficient_evidence" />);
    expect(screen.getByText('Insufficient evidence')).toBeInTheDocument();
  });

  it('distinguishes no evidence from insufficient evidence', () => {
    render(<StatusBadge status="no_evidence" />);
    expect(screen.getByText('No evidence')).toBeInTheDocument();
  });
});

describe('MasteryBar', () => {
  it('announces the mastery and target for screen readers', () => {
    render(<MasteryBar result={result()} targetLevel={3} />);
    const bar = screen.getByRole('img');
    expect(bar).toHaveAccessibleName('Mastery 71 percent, target level 3');
  });

  it('says there is no estimate when mastery is unknown', () => {
    render(<MasteryBar result={result({ mastery: null, status: 'no_evidence' })} />);
    expect(screen.getByRole('img')).toHaveAccessibleName(
      'No mastery estimate — no evidence recorded',
    );
  });

  it('marks an unasserted mastery visually distinctly', () => {
    // The 95%-course case: a high mastery that must not read as an achieved level.
    const { container } = render(
      <MasteryBar result={result({ mastery: 0.95, status: 'insufficient_evidence' })} />,
    );
    expect(container.querySelector('.mastery-fill-unasserted')).not.toBeNull();
  });
});

describe('Meter', () => {
  it('renders the value as a percentage', () => {
    render(<Meter value={0.412} label="Confidence" />);
    expect(screen.getByText('41%')).toBeInTheDocument();
  });
});

describe('evidenceTypeLabel', () => {
  it('humanises known evidence types', () => {
    expect(evidenceTypeLabel('course_completion')).toBe('Course completion');
    expect(evidenceTypeLabel('sme_verified')).toBe('Expert verified');
  });

  it('falls back readably for an unknown type', () => {
    expect(evidenceTypeLabel('some_new_type')).toBe('some new type');
  });
});
