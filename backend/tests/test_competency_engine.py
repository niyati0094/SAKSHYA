"""Tests for the deterministic competency engine.

These are the most important tests in the project: they prove the competency
number is reproducible arithmetic over evidence, not an opaque judgement.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.engines.competency import (
    CompetencyStatus,
    EvidenceInput,
    calculate_competency,
    level_for_mastery,
    recency_factor,
)
from app.engines.constants import (
    EVIDENCE_TYPE_WEIGHTS,
    MIN_EFFECTIVE_EVIDENCE,
    RECENCY_HALF_LIFE_DAYS,
)

NOW = datetime(2026, 8, 24, tzinfo=timezone.utc)


def ev(
    evidence_id: int,
    evidence_type: str,
    score: float,
    days_ago: int = 0,
    review_status: str = "accepted",
) -> EvidenceInput:
    return EvidenceInput(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        score=score,
        observed_at=NOW - timedelta(days=days_ago),
        review_status=review_status,
    )


# ---------------------------------------------------------------------------
# Determinism and reproducibility
# ---------------------------------------------------------------------------


def test_identical_inputs_produce_identical_output():
    evidence = [ev(1, "assessment", 0.7, 30), ev(2, "simulation", 0.6, 90)]

    first = calculate_competency(1, evidence, NOW)
    second = calculate_competency(1, evidence, NOW)

    assert first.mastery == second.mastery
    assert first.confidence == second.confidence
    assert first.status == second.status
    assert first.explanation == second.explanation


def test_evidence_order_does_not_change_the_result():
    a = ev(1, "assessment", 0.7, 30)
    b = ev(2, "simulation", 0.6, 90)

    assert calculate_competency(1, [a, b], NOW).mastery == (
        calculate_competency(1, [b, a], NOW).mastery
    )


def test_mastery_matches_a_hand_computation():
    """Recompute the weighted mean by hand and require an exact match."""
    evidence = [ev(1, "assessment", 0.8, 0), ev(2, "assessment", 0.4, 365)]

    # assessment weight 1.0; recency 1.0 and 0.5 (exactly one half-life).
    expected = (0.8 * 1.0 + 0.4 * 0.5) / (1.0 + 0.5)

    result = calculate_competency(1, evidence, NOW)
    assert result.mastery == pytest.approx(expected, abs=1e-4)


def test_recency_halves_at_exactly_one_half_life():
    observed = NOW - timedelta(days=RECENCY_HALF_LIFE_DAYS)
    assert recency_factor(observed, NOW) == pytest.approx(0.5, abs=1e-6)


def test_future_evidence_is_not_boosted_above_one():
    assert recency_factor(NOW + timedelta(days=10), NOW) == 1.0


# ---------------------------------------------------------------------------
# The core thesis: course completion is not proof of competency
# ---------------------------------------------------------------------------


def test_course_completion_is_the_weakest_evidence_type():
    weights = EVIDENCE_TYPE_WEIGHTS
    assert weights["course_completion"] == min(weights.values())
    assert weights["simulation"] > weights["assessment"] > weights["course_completion"]


def test_a_perfect_course_score_alone_establishes_nothing():
    """The headline behaviour: 100% on a course does not establish competency.

    Course completion is weighted 0.0, so it contributes no evidence at all -
    not merely insufficient evidence.
    """
    result = calculate_competency(1, [ev(1, "course_completion", 1.0, 40)], NOW)

    assert result.status == CompetencyStatus.NO_EVIDENCE
    assert result.level == 0, "no level may be asserted on course completion alone"
    assert result.mastery is None
    assert result.effective_evidence == 0.0
    assert any("weighted 0.0 by design" in line for line in result.explanation)


def test_a_simulation_outweighs_a_course_completion_at_the_same_score():
    course = calculate_competency(1, [ev(1, "course_completion", 0.9, 0)], NOW)
    simulation = calculate_competency(1, [ev(1, "simulation", 0.9, 0)], NOW)

    # Same score, but the simulation carries far more effective weight.
    assert simulation.effective_evidence > course.effective_evidence
    assert simulation.confidence > course.confidence


# ---------------------------------------------------------------------------
# Sufficiency: "I don't know yet" is a real answer
# ---------------------------------------------------------------------------


def test_no_evidence_reports_no_evidence():
    result = calculate_competency(1, [], NOW)

    assert result.status == CompetencyStatus.NO_EVIDENCE
    assert result.mastery is None
    assert result.level == 0
    assert result.confidence == 0.0


def test_unreviewed_evidence_does_not_count():
    result = calculate_competency(1, [ev(1, "practical_submission", 0.9, 5, "pending")], NOW)

    assert result.status == CompetencyStatus.NO_EVIDENCE
    assert result.counted_evidence_count == 0
    assert result.evidence_count == 1
    assert result.contributions[0].counted is False
    assert "not accepted" in result.contributions[0].excluded_reason


def test_rejected_evidence_does_not_count():
    result = calculate_competency(1, [ev(1, "assessment", 1.0, 1, "rejected")], NOW)
    assert result.counted_evidence_count == 0


def test_strong_varied_evidence_establishes_a_level():
    evidence = [
        ev(1, "assessment", 0.75, 20),
        ev(2, "simulation", 0.80, 40),
        ev(3, "practical_submission", 0.78, 60),
    ]
    result = calculate_competency(1, evidence, NOW)

    assert result.status == CompetencyStatus.ESTABLISHED
    assert result.level >= 3
    assert result.confidence > 0.7


# ---------------------------------------------------------------------------
# Confidence behaviour
# ---------------------------------------------------------------------------


def test_diversity_raises_confidence_at_equal_volume():
    """Three kinds of evidence should beat three of the same kind."""
    same = [ev(i, "assessment", 0.7, 30) for i in range(1, 4)]
    varied = [
        ev(1, "assessment", 0.7, 30),
        ev(2, "simulation", 0.7, 30),
        ev(3, "peer_review", 0.7, 30),
    ]

    assert (
        calculate_competency(1, varied, NOW).confidence_breakdown.diversity
        > calculate_competency(1, same, NOW).confidence_breakdown.diversity
    )


def test_conflicting_scores_lower_agreement():
    consistent = [ev(1, "assessment", 0.7, 10), ev(2, "simulation", 0.7, 10)]
    conflicting = [ev(1, "assessment", 0.2, 10), ev(2, "simulation", 0.95, 10)]

    assert (
        calculate_competency(1, conflicting, NOW).confidence_breakdown.agreement
        < calculate_competency(1, consistent, NOW).confidence_breakdown.agreement
    )


def test_single_item_agreement_is_neutral_not_perfect():
    """One item cannot agree with anything, so it must not score a perfect 1.0."""
    result = calculate_competency(1, [ev(1, "simulation", 0.9, 5)], NOW)
    assert result.confidence_breakdown.agreement == 0.5


def test_stale_evidence_lowers_confidence():
    fresh = calculate_competency(1, [ev(1, "simulation", 0.8, 5)], NOW)
    stale = calculate_competency(1, [ev(1, "simulation", 0.8, 900)], NOW)

    assert stale.confidence < fresh.confidence
    assert stale.confidence_breakdown.recency < fresh.confidence_breakdown.recency


def test_limiting_factor_identifies_the_weakest_component():
    """One recent, high-volume evidence type: diversity should be the constraint."""
    evidence = [ev(i, "assessment", 0.7, 5) for i in range(1, 6)]
    result = calculate_competency(1, evidence, NOW)

    assert result.confidence_breakdown.limiting_factor == "diversity"


# ---------------------------------------------------------------------------
# Auditability
# ---------------------------------------------------------------------------


def test_contribution_shares_sum_to_one():
    evidence = [
        ev(1, "assessment", 0.6, 10),
        ev(2, "simulation", 0.8, 100),
        ev(3, "course_completion", 0.9, 300),
    ]
    result = calculate_competency(1, evidence, NOW)

    counted = [c for c in result.contributions if c.counted]
    assert sum(c.contribution_share for c in counted) == pytest.approx(1.0, abs=1e-3)


def test_excluded_evidence_has_zero_contribution():
    evidence = [ev(1, "assessment", 0.7, 10), ev(2, "assessment", 0.9, 10, "pending")]
    result = calculate_competency(1, evidence, NOW)

    excluded = next(c for c in result.contributions if c.evidence_id == 2)
    assert excluded.contribution_share == 0.0
    assert excluded.effective_weight == 0.0


def test_every_result_carries_an_explanation():
    for evidence in ([], [ev(1, "course_completion", 0.9, 10)], [ev(1, "simulation", 0.8, 10)]):
        result = calculate_competency(1, evidence, NOW)
        assert result.explanation, "every outcome must explain itself"
        assert all(isinstance(line, str) and line for line in result.explanation)


@pytest.mark.parametrize(
    "mastery,expected_level",
    [(0.0, 1), (0.39, 1), (0.40, 2), (0.59, 2), (0.60, 3), (0.79, 3), (0.80, 4), (1.0, 4)],
)
def test_level_bands(mastery, expected_level):
    assert level_for_mastery(mastery) == expected_level
